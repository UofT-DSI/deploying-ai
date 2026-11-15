import base64
import importlib.util
import json
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

script = Path(__file__).resolve().parents[1] / "review.py"
spec = importlib.util.spec_from_file_location("assignment_review", script)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class SnapshotTests(unittest.TestCase):
    def test_wrapped_base64_content_is_accepted(self):
        pr = {"number": 7, "head": {"sha": "abc123", "repo": {"full_name": "ada/course"}}}
        encoded = base64.b64encode(b'{"cells":[]}').decode()
        payload = {"content": encoded[:8] + "\n  " + encoded[8:], "encoding": "base64"}
        with patch.object(review, "github_api", side_effect=[payload, [], pr]):
            self.assertEqual(review.fetch_assignment_snapshot("ada/course", pr).notebook, {"cells": []})
    def test_snapshot_uses_selected_head_and_assigned_path(self):
        pr = {
            "number": 7,
            "head": {"sha": "abc123", "ref": "assignment-1", "repo": {"full_name": "ada/course"}},
            "base": {"sha": "base123"},
        }
        notebook = {"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
        payload = {"content": base64.b64encode(json.dumps(notebook).encode()).decode(), "encoding": "base64"}
        with patch.object(review, "github_api", side_effect=[payload, [{"filename": "02_activities/assignment_1.ipynb"}], pr]) as api:
            snapshot = review.fetch_assignment_snapshot("ada/course", pr)
        self.assertEqual(snapshot.notebook, notebook)
        self.assertEqual(snapshot.sha, "abc123")
        self.assertEqual(snapshot.changed_paths, ("02_activities/assignment_1.ipynb",))
        self.assertIn("ref=abc123", api.call_args_list[0].args[0])
        self.assertIn("02_activities/assignment_1.ipynb", api.call_args_list[0].args[0])

    def test_moving_pr_is_rejected(self):
        pr = {"number": 7, "head": {"sha": "abc123", "repo": {"full_name": "ada/course"}}}
        payload = {"content": base64.b64encode(b'{"cells":[]}').decode(), "encoding": "base64"}
        with patch.object(review, "github_api", side_effect=[payload, [], {"head": {"sha": "new123"}}]), \
             self.assertRaises(review.LookupFailure):
            review.fetch_assignment_snapshot("ada/course", pr)

    def test_deleted_head_repo_is_lookup_error(self):
        pr = {"number": 7, "head": {"sha": "abc123", "repo": None}}
        with self.assertRaises(review.LookupFailure):
            review.fetch_assignment_snapshot("ada/course", pr)

    def test_invalid_notebook_is_student_specific_failure(self):
        pr = {"number": 7, "head": {"sha": "abc123", "repo": {"full_name": "ada/course"}}}
        payload = {"content": base64.b64encode(b'{"cells":[null]}').decode(), "encoding": "base64"}
        with patch.object(review, "github_api", return_value=payload), \
             self.assertRaises(review.NotebookMissing):
            review.fetch_assignment_snapshot("ada/course", pr)

    def test_invalid_base64_is_student_specific_failure(self):
        pr = {"number": 7, "head": {"sha": "abc123", "repo": {"full_name": "ada/course"}}}
        with patch.object(review, "github_api", return_value={"content": "not base64!", "encoding": "base64"}), \
             self.assertRaises(review.NotebookMissing):
            review.fetch_assignment_snapshot("ada/course", pr)

    def test_malformed_pr_files_are_lookup_error(self):
        pr = {"number": 7, "head": {"sha": "abc123", "repo": {"full_name": "ada/course"}}}
        payload = {"content": base64.b64encode(b'{"cells":[]}').decode(), "encoding": "base64"}
        with patch.object(review, "github_api", side_effect=[payload, {"bad": "shape"}, pr]), \
             self.assertRaises(review.LookupFailure):
            review.fetch_assignment_snapshot("ada/course", pr)


class RubricTests(unittest.TestCase):
    def test_course_evaluate_call_counts_as_metric_application(self):
        notebook = {"cells": [{"cell_type": "code", "source": [
            ("from deepeval.metrics import GEval, SummarizationMetric\n"
            "summary_metric = SummarizationMetric(assessment_questions=[])\n"
            "tone_metric = GEval(evaluation_steps=[], name='Tonality')\n"
            "evaluate(test_cases=[case], metrics=[summary_metric, tone_metric])\n")
        ]}]}
        rows = {row.name: row for row in review.assess(notebook)}
        self.assertEqual(rows["Summarization evaluation"].parts[-1].earned, 2)
        self.assertEqual(rows["G-Eval quality checks"].parts[2].earned, 2)

    def test_metric_defined_in_prior_cell_is_applied(self):
        notebook = {"cells": [
            {"cell_type": "code", "source": ["summary_metric = SummarizationMetric(assessment_questions=[])"]},
            {"cell_type": "code", "source": ["evaluate(test_cases=[case], metrics=[summary_metric])"]},
        ]}
        row = next(row for row in review.assess(notebook) if row.name == "Summarization evaluation")
        self.assertEqual(row.parts[-1].earned, 2)
        self.assertIn("Code cell 2", row.parts[-1].evidence)

    def test_unrelated_output_does_not_score_generated_fields(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["print('article')"]}]}
        executed = {"cells": [{"outputs": [{"output_type": "stream", "text":
            "A professional career article.\n\nSummary: " + "long " * 1001}]}]}
        generated = next(row for row in review.assess(notebook, executed) if row.name == "Generated content")
        self.assertEqual(generated.parts[0].earned, 0)
        self.assertEqual(generated.parts[1].earned, 0)
        self.assertEqual(generated.parts[3].earned, 0)

    def test_structured_pair_requires_output(self):
        notebook = {"cells": [{"cell_type": "code", "source": [
            ("class Scores:\n    SummarizationScore: float\n    SummarizationReason: str\n"
            "raise NameError('missing')\n")
        ]}]}
        rows = {row.name: row for row in review.assess(notebook)}
        self.assertEqual(rows["Structured evaluation result"].parts[0].earned, 0)

    def test_revised_summary_evaluation_requires_observed_result(self):
        notebook = {"cells": [
            {"cell_type": "markdown", "source": ["# Enhancement"]},
            {"cell_type": "code", "source": ["revised = improve(summary)\nmetric.measure(revised)\nprint(metric.score, metric.reason)"]},
        ]}
        failed = {"cells": [
            {"outputs": []},
            {"outputs": [
                {"output_type": "stream", "text": "Score: 0.8\nReason: old result"},
                {"output_type": "error", "ename": "NameError", "evalue": "improve is missing"},
            ]},
        ]}
        observed = {"cells": [
            {"outputs": []},
            {"outputs": [{"output_type": "stream", "text": "Score: 0.8\nReason: Improved clarity"}]},
        ]}
        def earned(executed):
            row = next(row for row in review.assess(notebook, executed) if row.name == "Enhancement and reflection")
            return row.parts[2].earned
        self.assertEqual(earned(failed), 0)
        self.assertEqual(earned(observed), 3)

        notebook["cells"][1]["source"] = ["revised = improve(summary)\nmetric.measure(revised)"]
        notebook["cells"].append({"cell_type": "code", "source": [
            ("display(Markdown(f'**Score**: {metric.score}'))\n"
             "display(Markdown(f'**Reason**: {metric.reason}'))")
        ]})
        course_style = {"cells": [
            {"outputs": []},
            {"outputs": []},
            {"outputs": [
                {"output_type": "display_data", "data": {"text/markdown": "**Score**: 0.8"}},
                {"output_type": "display_data", "data": {"text/markdown": "**Reason**: Improved clarity"}},
            ]},
        ]}
        row = next(row for row in review.assess(notebook, course_style) if row.name == "Enhancement and reflection")
        self.assertEqual(row.parts[2].earned, 3)
        self.assertIn("Code cell 2", row.parts[2].evidence)
        self.assertIn("Output cell 3", row.parts[2].evidence)

    def test_revised_summary_does_not_borrow_another_metric_result(self):
        notebook = {"cells": [
            {"cell_type": "markdown", "source": ["# Enhancement"]},
            {"cell_type": "code", "source": ["metric.measure(revised)"]},
            {"cell_type": "code", "source": [
                ("display(Markdown(f'**Score**: {other_metric.score}'))\n"
                 "display(Markdown(f'**Reason**: {metric.reason}'))")
            ]},
        ]}
        executed = {"cells": [
            {"outputs": []},
            {"outputs": []},
            {"outputs": [
                {"output_type": "display_data", "data": {"text/markdown": "**Score**: 0.8"}},
                {"output_type": "display_data", "data": {"text/markdown": "**Reason**: Improved clarity"}},
            ]},
        ]}
        row = next(row for row in review.assess(notebook, executed) if row.name == "Enhancement and reflection")
        self.assertEqual(row.parts[2].earned, 0)

        notebook["cells"][2]["source"] = ["display(Markdown(f'**Score**: {metric.score}'))"]
        notebook["cells"].append({"cell_type": "code", "source": ["display(Markdown(f'**Reason**: {metric.reason}'))"]})
        executed["cells"][2]["outputs"] = executed["cells"][2]["outputs"][:1]
        executed["cells"].append({"outputs": [
            {"output_type": "display_data", "data": {"text/markdown": "**Reason**: Improved clarity"}}
        ]})
        row = next(row for row in review.assess(notebook, executed) if row.name == "Enhancement and reflection")
        self.assertEqual(row.parts[2].earned, 0)

    def test_revised_summary_comment_is_not_an_evaluation(self):
        notebook = {"cells": [
            {"cell_type": "markdown", "source": ["# Enhancement"]},
            {"cell_type": "code", "source": [
                "# metric.measure(revised)\nprint('Score: 0.8\\nReason: old result')"
            ]},
        ]}
        executed = {"cells": [
            {"outputs": []},
            {"outputs": [{"output_type": "stream", "text": "Score: 0.8\nReason: old result"}]},
        ]}
        row = next(row for row in review.assess(notebook, executed) if row.name == "Enhancement and reflection")
        self.assertEqual(row.parts[2].earned, 0)

    def test_grade_boundaries(self):
        self.assertEqual([review.grade_label(x) for x in (24, 25, 64, 65)],
                         ["Missing", "Incomplete", "Incomplete", "Complete"])
        self.assertEqual(review.grade_label(90, True), "Pending")

    def test_each_criterion_has_the_agreed_point_cap(self):
        rows = review.assess({"cells": []})
        self.assertEqual({row.name: row.available for row in rows}, {
            "Source selection and loading": 10,
            "Generation implementation": 15,
            "Structured generation": 15,
            "Generated content": 10,
            "Summarization evaluation": 10,
            "G-Eval quality checks": 15,
            "Structured evaluation result": 10,
            "Enhancement and reflection": 15,
        })

    def test_partial_credit_and_pending_execution(self):
        notebook = {"cells": [{"cell_type": "code", "source": [
            ("from pydantic import BaseModel\nclass Result(BaseModel):\n"
            "    Author: str\n    Title: str\n    Relevance: str\n    Summary: str\n"
            "    Tone: str\n    InputTokens: int\n"
            "questions = ['How does the author define feedback?', 'Why is strength important?',"
            " 'What evidence supports the thesis?']\n"
            "from deepeval.metrics import SummarizationMetric\n"
            "metric = SummarizationMetric(assessment_questions=questions)\n"
            "from openai import OpenAI\nclient = OpenAI()\n")
        ]}]}
        rows = review.assess(notebook, blocked="API unavailable")
        self.assertEqual(sum(row.available for row in rows), 100)
        structured = next(row for row in rows if row.name == "Structured generation")
        self.assertEqual(structured.available, 15)
        self.assertEqual(structured.earned, 9)
        summary = next(row for row in rows if row.name == "Summarization evaluation")
        self.assertEqual(summary.parts[1].earned, 3)
        self.assertTrue(any(row.pending for row in rows))

    def test_g_eval_questions_are_counted_per_metric(self):
        notebook = {"cells": [{"cell_type": "code", "source": [
            ("from deepeval.metrics import GEval\n"
            "tone = GEval(name='Tonality', evaluation_steps=['Does the voice stay formal?',"
            " 'Is the chosen tone recognizable?', 'Does wording remain consistent?'])\n"
            "safety = GEval(name='Safety', evaluation_steps=['Does it avoid harmful advice?'])\n"
            "tone.measure(case)\n")
        ]}]}
        row = next(item for item in review.assess(notebook) if item.name == "G-Eval quality checks")
        self.assertEqual(row.available, 15)
        self.assertAlmostEqual(row.earned, 4.4)

    def test_template_instructions_do_not_count_as_student_reflection(self):
        template = json.loads((Path(__file__).resolve().parents[3] / "02_activities" / "assignment_1.ipynb").read_text(encoding="utf-8"))
        row = next(item for item in review.assess(template) if item.name == "Enhancement and reflection")
        self.assertEqual(row.parts[-1].earned, 0)
        template["cells"].append({"cell_type": "markdown", "source": [
            "The revised summary improved clarity, but the controls still miss source attribution."]})
        row = next(item for item in review.assess(template) if item.name == "Enhancement and reflection")
        self.assertEqual(row.parts[-1].earned, 3)

    def test_report_keeps_hygiene_outside_points_and_redacts_key(self):
        student = review.make_student("Ada", "ada@example.com", "https://github.com/ada/course/pulls")
        pr = {"html_url": "https://github.com/ada/course/pull/7"}
        snapshot = review.AssignmentSnapshot("abc123", {"cells": []}, ("02_activities/assignment_1.ipynb", "extra.py"), "wrong-name")
        rows = review.assess({"cells": [{"cell_type": "code", "source": ["from openai import OpenAI\nclient = OpenAI()"]}]}, blocked="unavailable")
        with tempfile.TemporaryDirectory() as tmp, patch.dict(review.os.environ, {"OPENAI_API_KEY": "secret-value"}):
            path = Path(tmp) / "report.md"
            review.write_assignment_report(path, student, review.Result("submitted", pr, "closed"), snapshot, rows, "secret-value")
            report = path.read_text(encoding="utf-8")
        self.assertIn("Pending", report)
        self.assertIn("Pending/", report)
        self.assertIn("Percentage: pending", report)
        self.assertIn("PR state: closed", report)
        self.assertIn("## Submission format (outside points)", report)
        self.assertIn("wrong-name", report)
        self.assertNotIn("secret-value", report)

    def test_report_records_assigned_pdf_substitution_without_local_path(self):
        student = review.make_student("Ada", "ada@example.com", "https://github.com/ada/course/pulls")
        pr = {"html_url": "https://github.com/ada/course/pull/7"}
        notebook = {"cells": [{"cell_type": "code", "source": ["path = '/Users/ada/Downloads/managing_oneself.pdf'"]}]}
        snapshot = review.AssignmentSnapshot("abc123", notebook, ("02_activities/assignment_1.ipynb",), "assignment-1")
        rows = review.assess(notebook)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            review.write_assignment_report(path, student, review.Result("submitted", pr, "open"), snapshot, rows,
                                           None, substitutions=[{"cell": 1, "article": "managing_oneself.pdf"}])
            report = path.read_text(encoding="utf-8")
        self.assertIn("Code cell 1: managing_oneself.pdf", report)
        self.assertNotIn("/Users/ada/Downloads", report)

    def test_student_file_failure_retains_earlier_observed_output(self):
        notebook = {"cells": [
            {"cell_type": "code", "source": ["print(result)"]},
            {"cell_type": "code", "source": ["open('/Users/ada/private/resume.txt')"]},
        ]}
        executed = {"cells": [
            {"outputs": [{"output_type": "stream", "text":
                          "Relevance: Relevant to professional growth\nSummary: A concise source summary\nTone: professional"}]},
            {"outputs": [{"output_type": "error", "ename": "FileNotFoundError", "evalue": "missing"}]},
        ]}
        generated = next(row for row in review.assess(notebook, executed) if row.name == "Generated content")
        self.assertGreater(generated.earned, 0)
        self.assertEqual(generated.parts[0].earned, 2)
        self.assertEqual(generated.parts[1].earned, 2)


class CliReportTests(unittest.TestCase):
    def test_substitution_record_does_not_carry_to_next_student(self):
        pr = {"number": 7, "title": "Assignment 1", "head": {"sha": "abc123", "ref": "assignment-1"},
              "state": "open", "html_url": "https://github.com/ada/course/pull/7"}
        notebook = {"cells": [{"cell_type": "code", "source": ["print('done')"]}]}
        snapshot = review.AssignmentSnapshot("abc123", notebook, ("02_activities/assignment_1.ipynb",), "assignment-1")
        first = {"cells": [{"outputs": []}], "metadata": {"assignment_review": {"substitutions": [
            {"cell": 1, "article": "managing_oneself.pdf"}]}}}
        second = {"cells": [{"outputs": []}], "metadata": {"assignment_review": {"substitutions": []}}}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(review, "fetch_prs", return_value=[pr]), \
                 patch.object(review, "fetch_assignment_snapshot", return_value=snapshot), \
                 patch.object(review, "prepare_container", return_value=None), \
                 patch.object(review, "run_notebook", side_effect=[(first, None), (second, None)]):
                status = review.main(["--student", "Ada", "ada@example.com", "https://github.com/ada/course/pulls",
                                      "--student", "Grace", "grace@example.com", "https://github.com/grace/course/pulls",
                                      "--assignment", "1", "--output-dir", tmp])
            reports = sorted(Path(tmp).glob("assignment-1-review-*-student-*.md"))
            self.assertEqual(status, 0)
            self.assertEqual(len(reports), 2)
            self.assertIn("managing_oneself.pdf (course copy)", reports[0].read_text(encoding="utf-8"))
            self.assertNotIn("Assigned PDF substitutions", reports[1].read_text(encoding="utf-8"))

    def test_malformed_execution_does_not_stop_next_student_report(self):
        pr = {"number": 7, "title": "Assignment 1", "head": {"sha": "abc123", "ref": "assignment-1"},
              "state": "open", "html_url": "https://github.com/ada/course/pull/7"}
        notebook = {"cells": [{"cell_type": "code", "source": ["from openai import OpenAI"]}]}
        snapshot = review.AssignmentSnapshot("abc123", notebook, ("02_activities/assignment_1.ipynb",), "assignment-1")
        malformed = {"cells": [{"outputs": [{"output_type": "display_data", "data": "invalid"}]}]}
        valid = {"cells": [{"outputs": [{"output_type": "stream", "text": "completed extraction of enough article text to cite in this report"}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(review, "fetch_prs", return_value=[pr]), \
                 patch.object(review, "fetch_assignment_snapshot", return_value=snapshot), \
                 patch.object(review, "prepare_container", return_value=None), \
                 patch.object(review, "notebook_gateway", return_value=nullcontext(None)), \
                 patch.object(review, "capture_docker", side_effect=[
                     (json.dumps(malformed).encode(), b"", None), (json.dumps(valid).encode(), b"", None)
                 ]):
                status = review.main(["--student", "Broken", "broken@example.com", "https://github.com/broken/course/pulls",
                                      "--student", "Ada", "ada@example.com", "https://github.com/ada/course/pulls",
                                      "--assignment", "1", "--output-dir", tmp])
            reports = sorted(Path(tmp).glob("assignment-1-review-*-student-*.md"))
            self.assertEqual(status, 0)
            self.assertEqual(len(reports), 2)
            self.assertIn("invalid result shape", reports[0].read_text(encoding="utf-8"))
            self.assertIn("completed", reports[1].read_text(encoding="utf-8"))

    def test_invalid_cli_student_does_not_block_later_student(self):
        students, _, _ = review.parse_input(["--student", "Broken", "", "https://github.com/broken/course/pulls",
                                             "--student", "Ada", "ada@example.com", "https://github.com/ada/course/pulls",
                                             "--assignment", "1"])
        self.assertIn("email", students[0].missing)
        self.assertIsNone(students[1].issue)

    def test_bad_student_does_not_stop_valid_assignment_report(self):
        pr = {"number": 7, "title": "Assignment 1", "head": {"sha": "abc123", "ref": "assignment-1"},
              "state": "closed", "html_url": "https://github.com/ada/course/pull/7"}
        snapshot = review.AssignmentSnapshot("abc123", {"cells": [{"cell_type": "code", "source": ["from openai import OpenAI\nclient = OpenAI()"]}]}, ("02_activities/assignment_1.ipynb",), "assignment-1")
        with tempfile.TemporaryDirectory() as tmp:
            students = Path(tmp) / "students.csv"
            students.write_text("name,email,repo_url\nBroken,,https://github.com/broken/course/pulls\n"
                                "Ada,ada@example.com,https://github.com/ada/course/pulls\n", encoding="utf-8")
            with patch.object(review, "fetch_prs", return_value=[pr]), \
                 patch.object(review, "fetch_assignment_snapshot", return_value=snapshot), \
                 patch.object(review, "prepare_container", return_value="Docker unavailable"), \
                 patch.object(review, "run_notebook") as run:
                status = review.main(["--csv", str(students), "--assignment", "1", "--output-dir", tmp])
            self.assertEqual(status, 1)
            run.assert_not_called()
            reports = sorted(Path(tmp).glob("assignment-1-review-*-student-*.md"))
            self.assertEqual(len(reports), 2)
            self.assertIn("Assessment unavailable", reports[0].read_text(encoding="utf-8"))
            self.assertIn("Pending", reports[1].read_text(encoding="utf-8"))
            self.assertIn(pr["html_url"], reports[1].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
