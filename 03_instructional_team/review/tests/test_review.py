import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "review.py"
SPEC = importlib.util.spec_from_file_location("assignment_review", SCRIPT)
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class ReviewTests(unittest.TestCase):
    def test_cli_and_csv_intake(self):
        students, assignments, _ = review.parse_input([
            "--student", "Ada Lovelace", "ada@example.com", "https://github.com/ada/deploying-ai/pull/42",
            "--assignment", "1",
        ])
        self.assertEqual((students[0].name, students[0].repo), ("Ada Lovelace", "ada/deploying-ai"))
        self.assertEqual(assignments, (1,))

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "students.csv"
            csv_path.write_text("name,email,repo_url\nAda,ada@example.com,https://github.com/ada/deploying-ai/pull/42\nBob,bob@example.com,https://github.com/bob/production/pull/7\n", encoding="utf-8")
            students, _, _ = review.parse_input(["--csv", str(csv_path), "--assignment", "1"])
            self.assertEqual([student.name for student in students], ["Ada", "Bob"])

    def test_invalid_csv_record_warns_and_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "students.csv"
            csv_path.write_text("name,email,repo_url\nAda,,https://github.com/ada/deploying-ai/pull/42\n", encoding="utf-8")
            with self.assertLogs(level="WARNING"):
                students, _, _ = review.parse_input(["--csv", str(csv_path), "--assignment", "1"])
            self.assertEqual(students[0].missing, ("email",))
        with self.assertRaises(ValueError):
            review.parse_input(["--student", "Ada", "ada@example.com", "https://example.com/ada/repo/pull/1", "--assignment", "1"])

    def test_discovery_checks_branch_and_states(self):
        pr = {"number": 9, "head": {"ref": "assignment-1"}, "state": "closed", "merged_at": "2026-11-03T00:00:00Z", "html_url": "https://github.com/ada/deploying-ai/pull/9"}
        result = review.select_pr(pr, 1)
        self.assertEqual(result.primary["number"], 9)
        self.assertEqual(result.state, "merged")
        self.assertEqual(review.select_pr(pr, 2).kind, "warning")

    def test_direct_lookup_and_failure_are_distinct(self):
        pr = {"number": 2, "head": {"ref": "assignment-1"}, "state": "closed", "merged_at": None, "html_url": "https://github.com/ada/deploying-ai/pull/2"}
        with patch.object(review.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = json.dumps(pr)
            self.assertEqual(review.select_pr(review.fetch_pr("ada/deploying-ai", 2), 1).primary["number"], 2)
            self.assertNotIn("--paginate", run.call_args.args[0])
            run.return_value.returncode = 1
            run.return_value.stderr = "HTTP 403"
            with self.assertRaises(review.LookupFailure):
                review.fetch_pr("ada/deploying-ai", 2)

    def test_reports_and_reruns(self):
        student = review.Student("Ada / Lovelace", "ada@example.com", "https://github.com/ada/deploying-ai/pull/4", "ada/deploying-ai", 4)
        closed = review.Result("found", {"number": 4, "html_url": "https://github.com/ada/deploying-ai/pull/4"}, state="closed")
        with tempfile.TemporaryDirectory() as tmp:
            first = review.write_reports([(student, 1, closed), (student, 2, review.Result("warning", reason="Wrong assignment branch"))], Path(tmp))
            second = review.write_reports([(student, 1, review.Result("unverifiable", reason="HTTP 403"))], Path(tmp))
            self.assertNotEqual(first[0].parent, second[0].parent)
            text = first[0].read_text(encoding="utf-8")
            self.assertIn("PR status: closed", text)
            self.assertIn("ada@example.com", text)
            self.assertIn("Grading pending", text)
            self.assertIn("Status: Warning", first[1].read_text(encoding="utf-8"))
            self.assertIn("Verification could not be completed", second[0].read_text(encoding="utf-8"))
            self.assertEqual(first[0].name, first[0].resolve().name)

    def test_duplicate_students_get_separate_reports(self):
        student = review.make_student("Ada", "ada@example.com", "https://github.com/ada/deploying-ai/pull/4")
        with tempfile.TemporaryDirectory() as tmp:
            paths = review.write_reports([(student, 1, review.Result("warning", reason="Wrong branch")), (student, 1, review.Result("warning", reason="Wrong branch"))], Path(tmp))
            self.assertEqual(len({path.name for path in paths}), 2)
            self.assertTrue(all(path.exists() for path in paths))

    def test_main_skips_incomplete_row_and_checks_next_pr(self):
        pr = {"number": 4, "head": {"ref": "assignment-1"}, "state": "open", "merged_at": None, "html_url": "https://github.com/ada/deploying-ai/pull/4"}
        with tempfile.TemporaryDirectory() as tmp, patch.object(review, "fetch_pr", return_value=pr) as fetch:
            csv_path = Path(tmp) / "students.csv"
            csv_path.write_text("name,email,repo_url\nAda,,https://github.com/ada/deploying-ai/pull/3\nBob,bob@example.com,https://github.com/ada/deploying-ai/pull/4\n", encoding="utf-8")
            student_args = ["--csv", str(csv_path), "--assignment", "1"]
            result = review.main(student_args + ["--output-dir", tmp])
            self.assertEqual(result, 1)
            fetch.assert_called_once_with("ada/deploying-ai", 4)
            self.assertEqual(len(list(Path(tmp).rglob("*.md"))), 2)


if __name__ == "__main__":
    unittest.main()
