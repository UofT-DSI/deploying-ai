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
            "--student", "Ada Lovelace", "ada@example.com", "https://github.com/ada/deploying-ai",
            "--assignment", "both",
        ])
        self.assertEqual((students[0].name, students[0].repo), ("Ada Lovelace", "ada/deploying-ai"))
        self.assertEqual(assignments, (1, 2))

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "students.csv"
            csv_path.write_text("name,email,repo_url\nAda,ada@example.com,https://github.com/ada/deploying-ai\nBob,bob@example.com,https://github.com/bob/production\n", encoding="utf-8")
            students, _, _ = review.parse_input(["--csv", str(csv_path), "--assignment", "1"])
            self.assertEqual([student.name for student in students], ["Ada", "Bob"])

    def test_invalid_intake_stops_before_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "students.csv"
            csv_path.write_text("name,email,repo_url\nAda,,https://github.com/ada/deploying-ai\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "row 2"):
                review.parse_input(["--csv", str(csv_path), "--assignment", "1"])
        with self.assertRaises(ValueError):
            review.parse_input(["--student", "Ada", "ada@example.com", "https://example.com/ada/repo", "--assignment", "1"])

    def test_discovery_selects_newest_and_states(self):
        prs = [
            {"number": 4, "created_at": "2026-11-01T00:00:00Z", "head": {"ref": "assignment-1"}, "state": "closed", "merged_at": None, "html_url": "https://github.com/ada/deploying-ai/pull/4"},
            {"number": 9, "created_at": "2026-11-02T00:00:00Z", "head": {"ref": "assignment-1"}, "state": "closed", "merged_at": "2026-11-03T00:00:00Z", "html_url": "https://github.com/ada/deploying-ai/pull/9"},
            {"number": 12, "created_at": "2026-11-04T00:00:00Z", "head": {"ref": "assignment-2"}, "state": "open", "merged_at": None, "html_url": "https://github.com/ada/deploying-ai/pull/12"},
        ]
        result = review.select_pr(prs, 1)
        self.assertEqual(result.primary["number"], 9)
        self.assertEqual(result.state, "merged")
        self.assertEqual([pr["number"] for pr in result.other], [4])
        self.assertEqual(review.select_pr(prs, 2).state, "open")
        self.assertEqual(review.select_pr([], 1).kind, "absent")

    def test_paginated_lookup_and_failure_are_distinct(self):
        page_one = [{"number": 1, "head": {"ref": "other"}}]
        page_two = [{"number": 2, "head": {"ref": "assignment-1"}, "created_at": "2026-11-01T00:00:00Z", "state": "closed", "merged_at": None, "html_url": "https://github.com/ada/deploying-ai/pull/2"}]
        with patch.object(review.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = json.dumps([page_one, page_two])
            self.assertEqual(review.select_pr(review.fetch_prs("ada/deploying-ai"), 1).primary["number"], 2)
            self.assertIn("--paginate", run.call_args.args[0])
            run.return_value.returncode = 1
            run.return_value.stderr = "HTTP 403"
            with self.assertRaises(review.LookupFailure):
                review.fetch_prs("ada/deploying-ai")

    def test_reports_and_reruns(self):
        student = review.Student("Ada / Lovelace", "ada@example.com", "https://github.com/ada/deploying-ai", "ada/deploying-ai")
        closed = review.Result("found", {"number": 4, "html_url": "https://github.com/ada/deploying-ai/pull/4"}, [], "closed")
        with tempfile.TemporaryDirectory() as tmp:
            first = review.write_reports([(student, 1, closed), (student, 2, review.Result("absent"))], Path(tmp))
            second = review.write_reports([(student, 1, review.Result("unverifiable", reason="HTTP 403"))], Path(tmp))
            self.assertNotEqual(first[0].parent, second[0].parent)
            text = first[0].read_text(encoding="utf-8")
            self.assertIn("PR status: closed", text)
            self.assertIn("ada@example.com", text)
            self.assertIn("Grading pending", text)
            self.assertIn("No matching submission", first[1].read_text(encoding="utf-8"))
            self.assertIn("Verification could not be completed", second[0].read_text(encoding="utf-8"))
            self.assertEqual(first[0].name, first[0].resolve().name)

    def test_duplicate_students_get_separate_reports(self):
        student = review.make_student("Ada", "ada@example.com", "https://github.com/ada/deploying-ai")
        with tempfile.TemporaryDirectory() as tmp:
            paths = review.write_reports([(student, 1, review.Result("absent")), (student, 1, review.Result("absent"))], Path(tmp))
            self.assertEqual(len({path.name for path in paths}), 2)
            self.assertTrue(all(path.exists() for path in paths))

    def test_main_reuses_repository_lookup_for_both_assignments(self):
        student_args = ["--student", "Ada", "ada@example.com", "https://github.com/ada/deploying-ai", "--assignment", "both"]
        with tempfile.TemporaryDirectory() as tmp, patch.object(review.shutil, "which", return_value="gh"), patch.object(review, "fetch_prs", return_value=[]) as fetch:
            result = review.main(student_args + ["--output-dir", tmp])
            self.assertEqual(result, 0)
            fetch.assert_called_once_with("ada/deploying-ai")
            self.assertEqual(len(list(Path(tmp).rglob("*.md"))), 2)


if __name__ == "__main__":
    unittest.main()
