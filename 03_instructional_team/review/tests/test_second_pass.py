import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import review
from assignment_1_evidence import build_evidence
from assignment_1_judge import JudgeReview, Judgment, judge_review, rubric_specs
from assignment_1_reconcile import reconcile
from assignment_1_rubric import assess


class EvidenceTests(unittest.TestCase):
    def test_uses_current_outputs_and_redacts_identifiers(self):
        notebook = {"cells": [{"cell_type": "code", "source": [
            "print('ada@example.com', 'sk-test-secret')\n"],
            "outputs": [{"output_type": "stream", "text": "stale submitted output"}]}]}
        executed = {"cells": [{"outputs": [{"output_type": "stream", "text": "current trusted output"}]}]}
        bundle = build_evidence(notebook, executed, None, secrets=("sk-test-secret",))
        rendered = str(bundle.entries)
        self.assertIn("current trusted output", rendered)
        self.assertNotIn("stale submitted output", rendered)
        self.assertNotIn("ada@example.com", rendered)
        self.assertNotIn("sk-test-secret", rendered)
        self.assertEqual([(item.kind, item.cell) for item in bundle.entries], [("code", 1), ("output", 1)])

    def test_redacts_student_name_parts(self):
        notebook = {"cells": [{"cell_type": "markdown", "source": ["Ada wrote this for Lovelace."]}]}
        bundle = build_evidence(notebook, None, None, student_name="Ada Lovelace")
        self.assertNotIn("Ada", bundle.entries[0].text)
        self.assertNotIn("Lovelace", bundle.entries[0].text)

    def test_assigned_reference_follows_code_not_template_markdown(self):
        notebook = {"cells": [
            {"cell_type": "markdown", "source": ["Template suggests managing_oneself.pdf"]},
            {"cell_type": "code", "source": ["file_path = 'ai_report_2025 (2).pdf'"]},
        ]}
        with patch("assignment_1_evidence._assigned_pdf_text", return_value="trusted AI report") as source:
            bundle = build_evidence(notebook, None, None)
        source.assert_called_once_with("ai_report_2025.pdf")
        self.assertEqual(bundle.reference_note, "Trusted course reference: ai_report_2025.pdf.")

    def test_long_output_keeps_both_ends_and_marks_omission(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["print(result)"]}]}
        executed = {"cells": [{"outputs": [{"output_type": "stream", "text":
                     "Article starts here" + "x" * 30000 + "Score: 0.75 Reason: improved"}]}]}
        bundle = build_evidence(notebook, executed, None)
        output = bundle.entries[1].text
        self.assertIn("Article starts here", output)
        self.assertIn("Score: 0.75 Reason: improved", output)
        self.assertIn("middle characters omitted", output)
        self.assertLessEqual(len(output), 10000)

    def test_stream_chunks_share_one_citable_cell_output(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["print(result)"]}]}
        executed = {"cells": [{"outputs": [{"output_type": "stream", "text": "Score: 0.75"},
                                            {"output_type": "stream", "text": "Reason: improved"}]}]}
        bundle = build_evidence(notebook, executed, None)
        outputs = [item for item in bundle.entries if item.kind == "output"]
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0].cell, 1)
        self.assertIn("Score: 0.75", outputs[0].text)
        self.assertIn("Reason: improved", outputs[0].text)


class JudgeTests(unittest.TestCase):
    def test_request_is_independent_and_response_requires_every_part(self):
        criteria = assess({"cells": []})
        bundle = build_evidence({"cells": [{"cell_type": "code", "source": ["print('hello')"]}]}, None, None)
        specs = rubric_specs(criteria)
        payload = {"judgments": [{"part_id": spec.part_id, "points": 0, "status": "scored",
                                  "evidence": [], "reason": "No supporting evidence."} for spec in specs]}
        response = Mock(output_text=__import__("json").dumps(payload), status="completed", output=[])
        client = Mock()
        client.responses.create.return_value = response
        result = judge_review(bundle, specs, client=client)
        self.assertIsNone(result.issue)
        self.assertEqual(len(result.judgments), len(specs))
        request = client.responses.create.call_args.kwargs
        self.assertFalse(request["store"])
        self.assertNotIn("earned", str(request))
        self.assertNotIn("first-pass", str(request).lower())
        payload["judgments"].pop()
        response.output_text = __import__("json").dumps(payload)
        self.assertIn("missing", judge_review(bundle, specs, client=client).issue.lower())
        payload["judgments"].append({"part_id": specs[-1].part_id, "points": 0, "status": "scored",
                                     "evidence": [], "reason": "No supporting evidence."})
        payload["judgments"][0]["points"] = 1
        response.output_text = __import__("json").dumps(payload)
        self.assertIn("lacks evidence", judge_review(bundle, specs, client=client).issue.lower())


class ReconciliationTests(unittest.TestCase):
    def test_supported_structural_increase_and_decrease(self):
        notebook = {"cells": [{"cell_type": "code", "source": [
            "messages=[{'role': 'system', 'content': 'Summarize'}, {'role': 'user', 'content': 'text'}]\n",
            "model='gpt-5'\n"]}]}
        criteria = assess(notebook)
        generation = criteria[1]
        adjusted = list(generation.parts)
        adjusted[1] = replace(adjusted[1], earned=3)
        adjusted[3] = replace(adjusted[3], earned=0)
        criteria = criteria[:1] + (replace(generation, parts=tuple(adjusted)),) + criteria[2:]
        bundle = build_evidence(notebook, None, None)
        source = bundle.entries[0].text
        judgments = (
            Judgment("c02p04", 4, "scored", (("code", 1, source),), "Both roles appear."),
            Judgment("c02p02", 0, "scored", (("code", 1, "model='gpt-5'"),), "GPT-5 selected."),
        )
        result = reconcile(criteria, JudgeReview(judgments), bundle)
        generation = result.criteria[1]
        self.assertEqual(generation.parts[3].earned, 4)
        self.assertEqual(generation.parts[1].earned, 0)
        self.assertEqual([item.status for item in result.decisions], ["applied", "applied"])

    def test_gpt5_citation_cannot_remove_credit_when_other_model_is_used(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["model='gpt-5'\nmodel='gpt-4.1'"]}]}
        criteria = assess(notebook)
        bundle = build_evidence(notebook, None, None)
        result = reconcile(criteria, JudgeReview((Judgment("c02p02", 0, "scored",
                                                   (("code", 1, "model='gpt-5'"),), "GPT-5."),)), bundle)
        self.assertEqual(result.criteria[1].parts[1].earned, 3)
        self.assertEqual(result.decisions[0].status, "disputed")

    def test_semantic_or_bad_citation_stays_disputed(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["print('summary')"]}]}
        criteria = assess(notebook)
        bundle = build_evidence(notebook, None, None)
        judgments = (
            Judgment("c04p03", 2, "scored", (("code", 1, "print('summary')"),), "Faithful."),
            Judgment("c02p04", 4, "scored", (("code", 99, "system and user"),), "Roles."),
        )
        result = reconcile(criteria, JudgeReview(judgments), bundle)
        self.assertEqual([item.status for item in result.decisions], ["disputed", "disputed"])
        self.assertEqual(result.criteria[3].parts[2].earned, criteria[3].parts[2].earned)
        self.assertTrue(result.criteria[3].parts[2].pending)

    def test_bad_citation_on_same_score_does_not_create_pending(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["print('hello')"]}]}
        criteria = assess(notebook)
        bundle = build_evidence(notebook, None, None)
        review_result = JudgeReview((Judgment("c02p01", 0, "scored",
                                              (("code", 99, "missing"),), "No SDK."),))
        result = reconcile(criteria, review_result, bundle)
        self.assertEqual(result.decisions[0].status, "unverified")
        self.assertEqual(result.criteria[1].parts[0].earned, 0)
        self.assertFalse(result.criteria[1].parts[0].pending)

    def test_blocked_runtime_part_remains_unavailable_when_judge_says_zero(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["print(result)"]}]}
        criteria = assess(notebook, None, "Environment: API response failed")
        bundle = build_evidence(notebook, None, "Environment: API response failed")
        result = reconcile(criteria, JudgeReview((Judgment("c07p01", 0, "scored", (),
                                                  "No Score and Reason seen."),)), bundle)
        self.assertEqual(result.decisions[0].status, "unavailable")
        self.assertTrue(result.criteria[6].parts[0].pending)
        self.assertEqual(result.criteria[6].parts[0].earned, 0)

    def test_report_shows_original_revision_and_dispute(self):
        notebook = {"cells": [{"cell_type": "code", "source": [
            "messages=[{'role': 'system'}, {'role': 'user'}]"]}]}
        criteria = assess(notebook)
        row = criteria[1]
        parts = list(row.parts)
        parts[3] = replace(parts[3], earned=0)
        criteria = criteria[:1] + (replace(row, parts=tuple(parts)),) + criteria[2:]
        bundle = build_evidence(notebook, None, None)
        second = reconcile(criteria, JudgeReview((
            Judgment("c02p04", 4, "scored", (("code", 1, bundle.entries[0].text),), "Both roles present."),
            Judgment("c04p03", 2, "scored", (("code", 1, "messages"),), "Source faithful."),
        ), model="gpt-4.1"), bundle)
        student = review.make_student("Ada", "ada@example.com", "https://github.com/ada/course/pulls")
        snapshot = review.AssignmentSnapshot("abc123", notebook, ("02_activities/assignment_1.ipynb",), "assignment-1")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft.md"
            review.write_assignment_report(path, student, review.Result("submitted", {"html_url":
                                           "https://github.com/ada/course/pull/7"}, "open"),
                                           snapshot, second.criteria, None, second_pass=second)
            report = path.read_text(encoding="utf-8")
        self.assertIn("original 0, AI 4", report)
        self.assertIn("Applied: Generation implementation / Developer and user prompts", report)
        self.assertIn("Disputed: Generated content / Source-faithful summary", report)
        self.assertIn("Pending", report)
        self.assertIn("Facilitator confirmation is required", report)


if __name__ == "__main__":
    unittest.main()
