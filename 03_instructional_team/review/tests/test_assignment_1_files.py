import base64
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assignment_1_files import eligible_text_path, fetch_text_files


class AssignmentTextFilesTests(unittest.TestCase):
    def test_fetches_committed_text_from_selected_tree(self):
        raw = b"A valid source article \xe9\n"
        calls = []

        def api(endpoint):
            calls.append(endpoint)
            if "/git/commits/" in endpoint:
                return {"tree": {"sha": "tree-1"}}
            if "/git/trees/" in endpoint:
                return {"tree": [
                    {"path": "02_activities/documents/source.txt", "type": "blob", "mode": "100644",
                     "size": len(raw), "sha": "blob-1"},
                    {"path": "02_activities/.env.txt", "type": "blob", "mode": "100644",
                     "size": 4, "sha": "private"},
                ]}
            return {"encoding": "base64", "content": base64.b64encode(raw).decode()}

        files = fetch_text_files("student/repo", "head-1", api)
        self.assertEqual(files, {"02_activities/documents/source.txt": raw})
        self.assertTrue(all("private" not in call for call in calls))
        self.assertIn("repos/student/repo/git/commits/head-1", calls)

    def test_rejects_unsafe_paths_and_symlinks(self):
        for path in ("../source.txt", "documents/../source.txt", "source\\other.txt",
                     "02_activities/.secrets.txt", "keys/api_key.txt", "credentials.txt",
                     "05_src/utils/notes.txt", "file.py"):
            self.assertFalse(eligible_text_path(path), path)

        def api(endpoint):
            if "/git/commits/" in endpoint:
                return {"tree": {"sha": "tree-1"}}
            return {"tree": [{"path": "source.txt", "type": "blob", "mode": "120000",
                              "size": 8, "sha": "blob-1"}]}

        with self.assertRaisesRegex(ValueError, "Unsupported text-file entry"):
            fetch_text_files("student/repo", "head-1", api)

    def test_truncated_tree_is_unavailable(self):
        def api(endpoint):
            return {"tree": {"sha": "tree-1"}} if "/git/commits/" in endpoint else {"truncated": True, "tree": []}

        with self.assertRaisesRegex(ValueError, "truncated"):
            fetch_text_files("student/repo", "head-1", api)

    def test_text_containing_credential_is_not_staged(self):
        raw = b"API_GATEWAY_KEY=student-value"

        def api(endpoint):
            if "/git/commits/" in endpoint:
                return {"tree": {"sha": "tree-1"}}
            if "/git/trees/" in endpoint:
                return {"tree": [{"path": "notes.txt", "type": "blob", "mode": "100644",
                                  "size": len(raw), "sha": "blob-1"}]}
            return {"encoding": "base64", "content": base64.b64encode(raw).decode()}

        self.assertEqual(fetch_text_files("student/repo", "head-1", api), {})


if __name__ == "__main__":
    unittest.main()
