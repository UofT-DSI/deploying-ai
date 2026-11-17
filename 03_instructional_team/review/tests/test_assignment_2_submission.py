import base64
import importlib.util
import unittest
from pathlib import Path

script = Path(__file__).resolve().parents[1] / "assignment_2_submission.py"
spec = importlib.util.spec_from_file_location("assignment_2_submission", script)
submission = importlib.util.module_from_spec(spec)
import sys

sys.modules[spec.name] = submission
spec.loader.exec_module(submission)


def fixture_api(files, *, moved=False, extra_entries=()):
    calls = []
    blobs = {}
    entries = list(extra_entries)
    for index, (path, content) in enumerate(files.items()):
        sha = f"blob-{index}"
        entries.append({"path": f"05_src/assignment_chat/{path}", "type": "blob", "mode": "100644",
                        "size": len(content), "sha": sha})
        blobs[sha] = {"encoding": "base64", "content": base64.b64encode(content).decode("ascii")}

    def api(endpoint, paginate=False):
        calls.append((endpoint, paginate))
        if endpoint.endswith("/git/commits/head-sha"):
            return {"tree": {"sha": "tree-sha"}}
        if "/git/trees/" in endpoint:
            return {"truncated": False, "tree": entries}
        if "/git/blobs/" in endpoint:
            return blobs[endpoint.rsplit("/", 1)[-1]]
        if endpoint.endswith("/files?per_page=100"):
            return [{"filename": "05_src/assignment_chat/app.py"}]
        if endpoint.endswith("/pulls/7"):
            return {"head": {"sha": "new-sha" if moved else "head-sha"}}
        raise AssertionError(endpoint)

    return api, calls


class ProjectSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.pr = {"number": 7, "head": {"sha": "head-sha", "ref": "assignment-2",
                                         "repo": {"full_name": "student/deploying-ai"}}}

    def test_fetches_project_data_from_one_commit(self):
        api, calls = fixture_api({"app.py": b"print('hi')", "index/data.bin": b"data"},
                                 extra_entries=({"path": "05_src/assignment_chat/index", "type": "tree",
                                                 "mode": "040000", "sha": "index"},))
        snapshot = submission.fetch_project_snapshot("student/deploying-ai", self.pr, api)
        self.assertEqual(snapshot.sha, "head-sha")
        self.assertEqual(snapshot.files["index/data.bin"], b"data")
        self.assertEqual(snapshot.branch, "assignment-2")
        self.assertIn(("repos/student/deploying-ai/pulls/7/files?per_page=100", True), calls)

    def test_changed_head_is_unverifiable(self):
        api, _ = fixture_api({"app.py": b"print('hi')"}, moved=True)
        with self.assertRaisesRegex(submission.ProjectUnavailable, "head changed"):
            submission.fetch_project_snapshot("student/deploying-ai", self.pr, api)

    def test_symlink_and_excessive_file_are_rejected(self):
        api, _ = fixture_api({}, extra_entries=({"path": "05_src/assignment_chat/link", "type": "blob",
                                                 "mode": "120000", "size": 4, "sha": "link"},))
        with self.assertRaisesRegex(submission.ProjectUnavailable, "Unsupported"):
            submission.fetch_project_snapshot("student/deploying-ai", self.pr, api)
        api, _ = fixture_api({}, extra_entries=({"path": "05_src/assignment_chat/huge.bin", "type": "blob",
                                                 "mode": "100644", "size": submission.MAX_FILE_BYTES + 1,
                                                 "sha": "huge"},))
        with self.assertRaisesRegex(submission.ProjectUnavailable, "review limit"):
            submission.fetch_project_snapshot("student/deploying-ai", self.pr, api)

    def test_skips_secret_file(self):
        api, _ = fixture_api({"app.py": b"print('hi')", ".secrets": b"secret", ".env.local": b"secret"})
        snapshot = submission.fetch_project_snapshot("student/deploying-ai", self.pr, api)
        self.assertNotIn(".secrets", snapshot.files)
        self.assertNotIn(".env.local", snapshot.files)

    def test_rejects_path_normalization(self):
        for path in ("folder/../app.py", "folder//app.py", "folder/./app.py"):
            self.assertIsNone(submission._project_path("05_src/assignment_chat/" + path))


if __name__ == "__main__":
    unittest.main()
