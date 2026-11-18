import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

script = Path(__file__).resolve().parents[1] / "review.py"
spec = importlib.util.spec_from_file_location("assignment_review_listing", script)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ListingInputTests(unittest.TestCase):
    def test_pull_request_listing_url_identifies_repo(self):
        student = review.make_student("Ada", "ada@example.com", "https://github.com/ada/deploying-ai/pulls?q=is%3Apr")
        self.assertEqual(student.repo, "ada/deploying-ai")
        self.assertEqual(student.url, "https://github.com/ada/deploying-ai/pulls")
        self.assertEqual(review.make_student("Amir", "amir.haka@gmail.com", "https://www.github.com/amir318is/deploying-ai/pulls").repo, "amir318is/deploying-ai")
        self.assertEqual(review.make_student("Ada", "ada@example.com", "https://github.com/ada/deploying-ai/pull").url, student.url)
        with self.assertRaises(ValueError):
            review.make_student("Ada", "ada@example.com", "https://github.com/ada/deploying-ai/pull/42")

    def test_paginated_lookup_selects_newest_assignment_title(self):
        old = {"number": 4, "title": "Assignment 1 draft", "created_at": "2026-11-01T00:00:00Z", "head": {"ref": "other"}, "state": "closed", "merged_at": None, "html_url": "https://github.com/ada/deploying-ai/pull/4"}
        newer = {"number": 9, "title": "Assignment #1: final", "created_at": "2026-11-02T00:00:00Z", "head": {"ref": "other"}, "state": "open", "merged_at": None, "html_url": "https://github.com/ada/deploying-ai/pull/9"}
        with patch.object(review.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = json.dumps([[old], [newer]])
            prs = review.fetch_prs("ada/deploying-ai")
            self.assertIn("--paginate", run.call_args.args[0])
        self.assertEqual(review.select_pr(prs, 1).primary["number"], 9)
        self.assertEqual(review.select_pr(prs, 2).kind, "not_submitted")

    def test_branch_match_and_merged_state(self):
        pr = {"number": 10, "title": "My final submission", "created_at": "2026-11-03T00:00:00Z", "head": {"ref": "assignment-2"}, "state": "closed", "merged_at": "2026-11-04T00:00:00Z", "html_url": "https://github.com/ada/deploying-ai/pull/10"}
        result = review.select_pr([pr], 2)
        self.assertEqual(result.state, "merged")
        self.assertEqual(review.report_row(review.make_student("Ada", "ada@example.com", "https://github.com/ada/deploying-ai/pulls"), 2, result)["note"], "PR was closed by merging")

    def test_spelled_out_assignment_title(self):
        pr = {"number": 3, "title": "Assignment one done", "created_at": "2026-11-01T00:00:00Z", "head": {"ref": "other"}, "state": "open", "merged_at": None, "html_url": "https://github.com/amir318is/deploying-ai/pull/3"}
        self.assertEqual(review.select_pr([pr], 1).kind, "submitted")

    def test_lookup_failure_is_error_not_missing_submission(self):
        student = review.make_student("Ada", "ada@example.com", "https://github.com/ada/deploying-ai/pulls")
        with patch.object(review.subprocess, "run") as run:
            run.return_value.returncode = 1
            run.return_value.stderr = "HTTP 403"
            with self.assertRaises(review.LookupFailure):
                review.fetch_prs(student.repo)
        row = review.report_row(student, 1, review.Result("unverifiable", reason="HTTP 403"))
        self.assertEqual(row["status"], "error")
        self.assertEqual(row["note"], "HTTP 403")

    def test_one_csv_contains_submitted_missing_and_warning_rows(self):
        from assignment_2_submission import ProjectSnapshot

        submitted = {"number": 9, "title": "Assignment 2", "created_at": "2026-11-02T00:00:00Z", "head": {"ref": "assignment-2"}, "state": "closed", "merged_at": None, "html_url": "https://github.com/ada/deploying-ai/pull/9"}
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "students.csv"
            csv_path.write_text(
                "name,email,repo_url\n"
                "Ada,ada@example.com,https://github.com/ada/deploying-ai/pulls\n"
                "Bob,bob@example.com,https://github.com/bob/deploying-ai/pulls\n"
                "Cara,,https://github.com/cara/deploying-ai/pulls\n",
                encoding="utf-8",
            )
            snapshot = ProjectSnapshot(
                "head-sha", {"app.py": b"print('hello')"}, ("05_src/assignment_chat/app.py",), "assignment-2")
            with (patch.object(review, "fetch_prs", side_effect=[[submitted], []]) as fetch,
                  patch.object(review, "fetch_project_snapshot", return_value=snapshot),
                  patch.object(review, "build_image", return_value="Docker unavailable"),
                  patch.object(review, "secret_key", return_value=None)):
                status = review.main(["--csv", str(csv_path), "--assignment", "2", "--output-dir", tmp])
            self.assertEqual(status, 1)
            self.assertEqual(fetch.call_count, 2)
            reports = list(Path(tmp).glob("assignment-2-review-*.csv"))
            self.assertEqual(len(reports), 1)
            import csv
            with reports[0].open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["status"] for row in rows], ["submitted", "not_submitted", "warning"])
            self.assertEqual(rows[0]["pr_state"], "closed")
            self.assertEqual(rows[0]["pr_url"], submitted["html_url"])
            self.assertEqual(rows[2]["missing_items"], "email")
            self.assertEqual(rows[2]["input_row"], "4")
            self.assertEqual(len(list(Path(tmp).rglob("*.md"))), 3)

    def test_assignment_two_mixed_batch_keeps_separate_drafts(self):
        from assignment_2_submission import ProjectSnapshot

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "students.csv"
            csv_path.write_text("name,email,repo_url\n" + "".join(
                f"{name},{name.lower()}@example.com,https://github.com/{name.lower()}/course/pulls\n"
                for name in ("Ada", "Bob", "Cara")), encoding="utf-8")
            pr = {"number": 1, "title": "Assignment 2", "created_at": "2026-11-02T00:00:00Z",
                  "head": {"ref": "assignment-2"}, "state": "open", "merged_at": None,
                  "html_url": "https://github.com/example/course/pull/1"}
            snapshot = ProjectSnapshot("sha", {"app.py": b"chat = gr.ChatInterface(fn)\n"},
                                       ("05_src/assignment_chat/app.py",), "assignment-2")
            runtimes = [
                {"state": "observed", "exchanges": [{"id": "memory_set", "response": "Hello"}]},
                {"state": "unavailable", "reason": "App exited during startup", "exchanges": []},
                {"state": "unavailable", "reason": "Runner returned no valid result", "exchanges": []},
            ]
            with (patch.object(review, "fetch_prs", side_effect=[[pr], [pr], [pr]]),
                  patch.object(review, "fetch_project_snapshot", return_value=snapshot),
                  patch.object(review, "build_image", return_value=None),
                  patch.object(review, "run_project", side_effect=runtimes),
                  patch.object(review, "secret_key", return_value=None),
                  patch.object(review, "course_gateway_key", return_value=None)):
                self.assertEqual(review.main(["--csv", str(csv_path), "--assignment", "2",
                                              "--output-dir", tmp]), 0)
            drafts = sorted(Path(tmp).glob("assignment-2-review-*-student-*.md"))
            self.assertEqual(len(drafts), 3)
            contents = [path.read_text(encoding="utf-8") for path in drafts]
            self.assertIn("Student: Ada", contents[0])
            self.assertIn("App exited during startup", contents[1])
            self.assertIn("Runner returned no valid result", contents[2])
            self.assertTrue(all("at least" in content and "Independent AI" in content for content in contents))

    def test_missing_csv_column_is_recorded_as_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "students.csv"
            path.write_text("name,repo_url\nAda,https://github.com/ada/deploying-ai/pulls\n", encoding="utf-8")
            with self.assertLogs(level="WARNING"):
                students, _, _ = review.parse_input(["--csv", str(path), "--assignment", "1"])
            self.assertEqual(students[0].missing, ("email",))
            self.assertEqual(review.report_row(students[0], 1, review.Result("warning", reason=students[0].issue))["missing_items"], "email")


if __name__ == "__main__":
    unittest.main()
