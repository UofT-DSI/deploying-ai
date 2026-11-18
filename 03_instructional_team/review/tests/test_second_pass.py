import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import review
from assignment_1_composite import CompositeJudgment, CompositeReview, composite_review
from assignment_1_evidence import build_evidence
from assignment_1_judge import (
    Citation,
    JudgeReview,
    Judgment,
    judge_review,
    rubric_specs,
)
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
        self.assertEqual(request["model"], "gpt-6.1-terra")
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


class CompositeTests(unittest.TestCase):
    def test_composite_receives_both_scores_after_independent_review(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["messages=[{'role': 'system'}, {'role': 'user'}]"]}]}
        criteria = assess(notebook)
        bundle = build_evidence(notebook, None, None)
        specs = rubric_specs(criteria)
        independent = JudgeReview(tuple(Judgment(spec.part_id, 0, "scored", (), "No evidence.") for spec in specs))
        payload = {"judgments": [{"part_id": spec.part_id, "points": 0, "status": "scored",
                                  "evidence": [], "reason": "No award.", "review_needed": False} for spec in specs],
                   "encouragements": [], "improvements": []}
        target = next(item for item in payload["judgments"] if item["part_id"] == "c02p04")
        target.update(points=4, evidence=[{"kind": "code", "cell": 1, "excerpt": "'role': 'system'"}],
                      reason="System and user roles are present.", review_needed=True)
        client = Mock()
        client.responses.create.return_value = Mock(status="completed", output=[], output_text=json.dumps(payload))
        result = composite_review(criteria, independent, bundle, client=client)
        self.assertIsNone(result.issue)
        self.assertEqual(result.judgments[6].points, 4)
        self.assertTrue(result.judgments[6].review_needed)
        request = client.responses.create.call_args.kwargs
        self.assertEqual(request["model"], "gpt-6.1-terra")
        self.assertFalse(request["store"])
        sent = json.loads(request["input"])
        self.assertIn("non_ai", sent)
        self.assertIn("ai", sent)
        self.assertEqual(len(sent["evidence"]), len(bundle.entries))

    def test_composite_rejects_invalid_citation(self):
        criteria = assess({"cells": []})
        bundle = build_evidence({"cells": []}, None, None)
        specs = rubric_specs(criteria)
        independent = JudgeReview(tuple(Judgment(spec.part_id, 0, "scored", (), "No evidence.") for spec in specs))
        payload = {"judgments": [{"part_id": spec.part_id, "points": 0, "status": "scored",
                                  "evidence": [], "reason": "No award.", "review_needed": False} for spec in specs],
                   "encouragements": [], "improvements": []}
        payload["judgments"][0].update(points=1, evidence=[{"kind": "code", "cell": 99, "excerpt": "missing"}])
        client = Mock()
        client.responses.create.return_value = Mock(status="completed", output=[], output_text=json.dumps(payload))
        result = composite_review(criteria, independent, bundle, client=client)
        self.assertIsNone(result.issue)
        self.assertEqual(result.judgments[0].status, "unavailable")
        self.assertIn("citation", result.judgments[0].reason.lower())
        self.assertTrue(all(item.status == "scored" for item in result.judgments[1:]))

    def test_composite_rejects_uncited_score_reduction(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["print('article')"]}]}
        criteria = assess(notebook)
        first = criteria[0]
        parts = list(first.parts)
        parts[0] = replace(parts[0], earned=2, evidence="Code cell 1: print('article')")
        criteria = (replace(first, parts=tuple(parts)),) + criteria[1:]
        bundle = build_evidence(notebook, None, None)
        specs = rubric_specs(criteria)
        independent = JudgeReview(tuple(Judgment(spec.part_id, 0, "scored", (), "No evidence.")
                                        for spec in specs))
        payload = {"judgments": [{"part_id": spec.part_id, "points": 0, "status": "scored",
                                  "evidence": [], "reason": "No award.", "review_needed": False} for spec in specs],
                   "encouragements": [], "improvements": []}
        client = Mock()
        client.responses.create.return_value = Mock(status="completed", output=[], output_text=json.dumps(payload))
        composite = composite_review(criteria, independent, bundle, client=client)
        self.assertEqual(composite.judgments[0].status, "unavailable")
        self.assertEqual(composite.judgments[1].status, "scored")
        result = reconcile(criteria, independent, bundle, composite)
        self.assertEqual(result.criteria[0].parts[0].earned, 2)
        self.assertTrue(result.decisions[0].review_needed)

    def test_non_ai_evidence_is_redacted_before_composite_request(self):
        criteria = assess({"cells": []})
        first = criteria[0]
        parts = list(first.parts)
        parts[0] = replace(parts[0], evidence="ada@example.com used sk-test-secret")
        criteria = (replace(first, parts=tuple(parts)),) + criteria[1:]
        bundle = build_evidence({"cells": []}, None, None)
        independent = JudgeReview(tuple(Judgment(spec.part_id, 0, "scored", (), "No evidence.")
                                        for spec in rubric_specs(criteria)))
        client = Mock()
        client.responses.create.return_value = Mock(status="incomplete", output=[])
        composite_review(criteria, independent, bundle, client=client, secrets=("sk-test-secret",))
        payload = client.responses.create.call_args.kwargs["input"]
        self.assertNotIn("ada@example.com", payload)
        self.assertNotIn("sk-test-secret", payload)


class ReconciliationTests(unittest.TestCase):
    def test_semantic_disagreement_keeps_a_proposed_number(self):
        notebook = {"cells": [{"cell_type": "markdown", "source": ["The summary explains the article's claim."]}]}
        criteria = assess(notebook)
        bundle = build_evidence(notebook, None, None)
        independent = JudgeReview((Judgment("c04p03", 2, "scored",
                                              (("markdown", 1, "The summary explains"),), "Faithful summary."),))
        composite = CompositeReview((CompositeJudgment("c04p03", 1, "scored",
                                                       (Citation("markdown", 1, "The summary explains"),),
                                                       "The claim is present, but accuracy needs review.", True),))
        result = reconcile(criteria, independent, bundle, composite)
        self.assertEqual(result.criteria[3].parts[2].earned, 1)
        self.assertFalse(result.criteria[3].parts[2].pending)
        decision = next(item for item in result.decisions if item.part_id == "c04p03")
        self.assertEqual((decision.original, decision.proposed, decision.composite_score),
                         (criteria[3].parts[2].earned, 2, 1))
        self.assertTrue(decision.review_needed)

    def test_invalid_composite_citation_keeps_non_ai_points(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["print('hello')"]}]}
        criteria = assess(notebook)
        first = criteria[0]
        parts = list(first.parts)
        parts[0] = replace(parts[0], earned=2, evidence="Code cell 1: print('hello')")
        criteria = (replace(first, parts=tuple(parts)),) + criteria[1:]
        bundle = build_evidence(notebook, None, None)
        independent = JudgeReview((Judgment("c01p01", 2, "scored",
                                              (("code", 1, "print('hello')"),), "Observed."),))
        composite = CompositeReview((CompositeJudgment("c01p01", 0, "unavailable", (),
                                                       "Composite citation did not match the available evidence.", True),))
        result = reconcile(criteria, independent, bundle, composite)
        self.assertEqual(result.criteria[0].parts[0].earned, 2)
        self.assertEqual(result.decisions[0].composite_score, 2)
        self.assertEqual(result.decisions[0].status, "fallback")

    def test_uncited_direct_composite_reduction_keeps_non_ai_points(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["print('article')"]}]}
        criteria = assess(notebook)
        first = criteria[0]
        parts = list(first.parts)
        parts[0] = replace(parts[0], earned=2, evidence="Code cell 1: print('article')")
        criteria = (replace(first, parts=tuple(parts)),) + criteria[1:]
        bundle = build_evidence(notebook, None, None)
        independent = JudgeReview((Judgment("c01p01", 2, "scored",
                                              (("code", 1, "print('article')"),), "Observed."),))
        composite = CompositeReview((CompositeJudgment("c01p01", 0, "scored", (),
                                                       "No award.", False),))
        result = reconcile(criteria, independent, bundle, composite)
        self.assertEqual(result.criteria[0].parts[0].earned, 2)
        self.assertEqual(result.decisions[0].status, "fallback")

    def test_cited_composite_reduction_remains_a_reviewable_proposal(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["print('article')"]}]}
        criteria = assess(notebook)
        first = criteria[0]
        parts = list(first.parts)
        parts[0] = replace(parts[0], earned=2, evidence="Code cell 1: print('article')")
        criteria = (replace(first, parts=tuple(parts)),) + criteria[1:]
        bundle = build_evidence(notebook, None, None)
        independent = JudgeReview((Judgment("c01p01", 2, "scored",
                                              (("code", 1, "print('article')"),), "Observed."),))
        composite = CompositeReview((CompositeJudgment("c01p01", 0, "scored",
                                                       (Citation("code", 1, "print('article')"),),
                                                       "The cited code does not select the assigned article.", True),))
        result = reconcile(criteria, independent, bundle, composite)
        self.assertEqual(result.criteria[0].parts[0].earned, 0)
        self.assertEqual(result.decisions[0].status, "proposed")
        self.assertTrue(result.decisions[0].review_needed)

    def test_unavailable_ai_part_is_named_in_appendix(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["print('hello')"]}]}
        criteria = assess(notebook)
        bundle = build_evidence(notebook, None, None)
        independent = JudgeReview((Judgment("c01p01", 0, "unavailable", (), "Could not inspect source."),))
        second = reconcile(criteria, independent, bundle, CompositeReview(issue="Composite unavailable"))
        student = review.make_student("Ada", "ada@example.com", "https://github.com/ada/course/pulls")
        snapshot = review.AssignmentSnapshot("abc123", notebook, ("02_activities/assignment_1.ipynb",), "assignment-1")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft.md"
            review.write_assignment_report(path, student, review.Result("submitted", {"html_url":
                                           "https://github.com/ada/course/pull/7"}, "open"),
                                           snapshot, second.criteria, None, second_pass=second)
            report = path.read_text(encoding="utf-8")
        row = next(line for line in report.splitlines() if "Source selection and loading /" in line)
        self.assertIn("Unavailable: Could not inspect source.", row)

    def test_report_redacts_student_controlled_evidence(self):
        notebook = {"cells": []}
        criteria = assess(notebook)
        first = criteria[0]
        parts = list(first.parts)
        parts[0] = replace(parts[0], evidence="ada@example.com sk-test-secret | injected")
        criteria = (replace(first, parts=tuple(parts)),) + criteria[1:]
        student = review.make_student("Ada", "ada@example.com", "https://github.com/ada/course/pulls")
        snapshot = review.AssignmentSnapshot("abc123", notebook, ("02_activities/assignment_1.ipynb",), "assignment-1")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft.md"
            review.write_assignment_report(path, student, review.Result("submitted", {"html_url":
                                           "https://github.com/ada/course/pull/7"}, "open"),
                                           snapshot, criteria, None)
            report = path.read_text(encoding="utf-8")
        rubric = report.split("## Rubric", 1)[1]
        self.assertNotIn("sk-test-secret", rubric)
        self.assertNotIn("ada@example.com", rubric)
        self.assertIn("\\| injected", rubric)

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
        self.assertEqual(result.criteria[6].parts[0].pending_reason, "blocked")
        self.assertEqual(result.criteria[6].parts[0].earned, 0)

    def test_printed_usage_updates_proposed_total_and_appendix(self):
        notebook = {"cells": [
            {"cell_type": "code", "source": [
                ("response = client.chat.completions.parse(model='gpt-4o-mini', messages=[])\n"
                 "event = response.choices[0].message.parsed")]},
            {"cell_type": "code", "source": [
                "print(f'Relevance: {event.relevance}')\nprint(f'Summary: {event.summary}')"]},
            {"cell_type": "code", "source": [
                "output_tokens = response.usage.completion_tokens\nprint(f'Output: {output_tokens}')"]},
        ]}
        executed = {"cells": [
            {"outputs": []},
            {"outputs": [{"output_type": "stream", "text": "Relevance: work\nSummary: Short summary."}]},
            {"outputs": [{"output_type": "stream", "text": "Output: 253"}]},
        ]}
        criteria = assess(notebook, executed)
        bundle = build_evidence(notebook, executed, None)
        second = reconcile(criteria, JudgeReview((), issue="AI review unavailable"), bundle,
                           CompositeReview((), issue="Composite review unavailable"))
        student = review.make_student("Ada", "ada@example.com", "https://github.com/ada/course/pulls")
        snapshot = review.AssignmentSnapshot("abc123", notebook, ("02_activities/assignment_1.ipynb",), "assignment-1")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft.md"
            review.write_assignment_report(path, student, review.Result("submitted", {"html_url":
                                           "https://github.com/ada/course/pull/7"}, "open"),
                                           snapshot, second.criteria, None, second_pass=second)
            report = path.read_text(encoding="utf-8")
        score = sum(row.earned for row in second.criteria)
        self.assertIn(f"Proposed score: {score:g} / 100.", report)
        self.assertIn(f"Proposed classification: {review.grade_label(score, False)}", report)
        appendix = next(line for line in report.splitlines()
                        if line.startswith("| Generated content / Summary at most 1,000 tokens |"))
        self.assertIn("| 2/2:", appendix)
        self.assertIn("| 2/2: Composite review unavailable", appendix)
        self.assertNotIn("Pending/2", appendix)

    def test_report_shows_original_revision_and_dispute(self):
        notebook = {"cells": [{"cell_type": "code", "source": [
            "messages=[{'role': 'system'}, {'role': 'user'}]"]}]}
        criteria = assess(notebook)
        row = criteria[1]
        parts = list(row.parts)
        parts[3] = replace(parts[3], earned=0)
        criteria = criteria[:1] + (replace(row, parts=tuple(parts)),) + criteria[2:]
        bundle = build_evidence(notebook, None, None)
        independent = JudgeReview((
            Judgment("c02p04", 4, "scored", (("code", 1, bundle.entries[0].text),), "Both roles present."),
            Judgment("c04p03", 2, "scored", (("code", 1, "messages"),), "Source faithful."),
        ), model="gpt-4.1")
        composite = CompositeReview((
            CompositeJudgment("c02p04", 4, "scored", (Citation("code", 1, bundle.entries[0].text),),
                              "Both system and user roles are present.", False),
            CompositeJudgment("c04p03", 1, "scored", (Citation("code", 1, "messages"),),
                              "The summary's faithfulness needs checking.", True),
        ), model="gpt-4.1")
        second = reconcile(criteria, independent, bundle, composite)
        student = review.make_student("Ada", "ada@example.com", "https://github.com/ada/course/pulls")
        snapshot = review.AssignmentSnapshot("abc123", notebook, ("02_activities/assignment_1.ipynb",), "assignment-1")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft.md"
            review.write_assignment_report(path, student, review.Result("submitted", {"html_url":
                                           "https://github.com/ada/course/pull/7"}, "open"),
                                           snapshot, second.criteria, None, second_pass=second)
            report = path.read_text(encoding="utf-8")
        self.assertIn("Proposed score:", report)
        self.assertIn("Proposed classification:", report)
        self.assertIn("| Generated content / Summary at most 1,000 tokens | Pending/2:", report)
        self.assertIn("| Rubric element | Non-AI Review | AI Review | Composite Review |", report)
        self.assertIn("Both system and user roles are present", report)
        self.assertIn("The summary's faithfulness needs checking", report)
        self.assertNotIn("## Independent AI review", report)
        self.assertTrue(report.rstrip().endswith("|"))
        self.assertIn("Facilitator confirmation is required", report)


if __name__ == "__main__":
    unittest.main()
