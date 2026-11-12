import base64
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


script = Path(__file__).resolve().parents[1] / "review.py"
spec = importlib.util.spec_from_file_location("assignment_review", script)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class SnapshotTests(unittest.TestCase):
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
        with patch.object(review, "github_api", side_effect=[payload, [], {"head": {"sha": "new123"}}]):
            with self.assertRaises(review.LookupFailure):
                review.fetch_assignment_snapshot("ada/course", pr)

    def test_deleted_head_repo_is_lookup_error(self):
        pr = {"number": 7, "head": {"sha": "abc123", "repo": None}}
        with self.assertRaises(review.LookupFailure):
            review.fetch_assignment_snapshot("ada/course", pr)

    def test_invalid_notebook_is_student_specific_failure(self):
        pr = {"number": 7, "head": {"sha": "abc123", "repo": {"full_name": "ada/course"}}}
        payload = {"content": base64.b64encode(b'{"cells":[null]}').decode(), "encoding": "base64"}
        with patch.object(review, "github_api", return_value=payload):
            with self.assertRaises(review.NotebookMissing):
                review.fetch_assignment_snapshot("ada/course", pr)

    def test_invalid_base64_is_student_specific_failure(self):
        pr = {"number": 7, "head": {"sha": "abc123", "repo": {"full_name": "ada/course"}}}
        with patch.object(review, "github_api", return_value={"content": "not base64!", "encoding": "base64"}):
            with self.assertRaises(review.NotebookMissing):
                review.fetch_assignment_snapshot("ada/course", pr)

    def test_malformed_pr_files_are_lookup_error(self):
        pr = {"number": 7, "head": {"sha": "abc123", "repo": {"full_name": "ada/course"}}}
        payload = {"content": base64.b64encode(b'{"cells":[]}').decode(), "encoding": "base64"}
        with patch.object(review, "github_api", side_effect=[payload, {"bad": "shape"}, pr]):
            with self.assertRaises(review.LookupFailure):
                review.fetch_assignment_snapshot("ada/course", pr)


class RubricTests(unittest.TestCase):
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
            "from pydantic import BaseModel\nclass Result(BaseModel):\n"
            "    Author: str\n    Title: str\n    Relevance: str\n    Summary: str\n"
            "    Tone: str\n    InputTokens: int\n"
            "questions = ['How does the author define feedback?', 'Why is strength important?',"
            " 'What evidence supports the thesis?']\n"
            "from deepeval.metrics import SummarizationMetric\n"
            "metric = SummarizationMetric(assessment_questions=questions)\n"
            "from openai import OpenAI\nclient = OpenAI()\n"
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
            "from deepeval.metrics import GEval\n"
            "tone = GEval(name='Tonality', evaluation_steps=['Does the voice stay formal?',"
            " 'Is the chosen tone recognizable?', 'Does wording remain consistent?'])\n"
            "safety = GEval(name='Safety', evaluation_steps=['Does it avoid harmful advice?'])\n"
            "tone.measure(case)\n"
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


class CliReportTests(unittest.TestCase):
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
