import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


script = Path(__file__).resolve().parents[1] / "review.py"
spec = importlib.util.spec_from_file_location("assignment_review_pr_input", script)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class PullRequestInputTests(unittest.TestCase):
    def test_pr_url_is_parsed_and_looked_up_directly(self):
        student = review.make_student("Ada", "ada@example.com", "https://github.com/ada/deploying-ai/pull/42")
        self.assertEqual((student.repo, student.pr_number), ("ada/deploying-ai", 42))
        with patch.object(review.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = json.dumps({"number": 42, "head": {"ref": "assignment-1"}, "state": "closed", "merged_at": None, "html_url": student.url})
            self.assertEqual(review.fetch_pr(student.repo, student.pr_number)["number"], 42)
            self.assertIn("repos/ada/deploying-ai/pulls/42", run.call_args.args[0])
            self.assertNotIn("--paginate", run.call_args.args[0])

    def test_missing_csv_fields_warn_and_continue(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "students.csv"
            csv_path.write_text(
                "name,email,repo_url\n"
                "Ada,,https://github.com/ada/deploying-ai/pull/42\n"
                "Bob,bob@example.com,https://github.com/bob/deploying-ai/pull/7\n",
                encoding="utf-8",
            )
            students, assignments, _ = review.parse_input(["--csv", str(csv_path), "--assignment", "1"])
            self.assertEqual(assignments, (1,))
            self.assertEqual(len(students), 2)
            self.assertEqual(students[0].missing, ("email",))
            self.assertEqual(students[1].pr_number, 7)
            warning = review.report_text(students[0], 1, review.Result("warning", reason="Missing input: email"))
            self.assertIn("Status: Warning", warning)
            self.assertIn("Missing input: email", warning)

    def test_missing_csv_column_warns_for_each_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "students.csv"
            csv_path.write_text("name,repo_url\nAda,https://github.com/ada/deploying-ai/pull/42\nBob,https://github.com/bob/deploying-ai/pull/7\n", encoding="utf-8")
            with self.assertLogs(level="WARNING") as logs:
                students, _, _ = review.parse_input(["--csv", str(csv_path), "--assignment", "1"])
            self.assertEqual([student.missing for student in students], [("email",), ("email",)])
            self.assertIn("CSV row 2", logs.output[0])
            self.assertIn("CSV row 3", logs.output[1])

    def test_pr_branch_mismatch_is_warning(self):
        pr = {"number": 42, "head": {"ref": "assignment-2"}, "state": "open", "merged_at": None, "html_url": "https://github.com/ada/deploying-ai/pull/42"}
        result = review.select_pr(pr, 1)
        self.assertEqual(result.kind, "warning")
        self.assertIn("assignment-2", result.reason)


if __name__ == "__main__":
    unittest.main()
