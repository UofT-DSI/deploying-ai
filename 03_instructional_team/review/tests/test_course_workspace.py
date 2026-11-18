import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from course_workspace import substitute_assigned_pdfs


class CourseWorkspaceTests(unittest.TestCase):
    def test_unique_assigned_pdf_is_substituted_without_changing_original(self):
        source = "path = r'C:\\Users\\Ada\\Downloads\\Managing Oneself_Drucker_HBR.pdf'\nprint(path)"
        notebook = {"cells": [{"cell_type": "code", "source": source}], "metadata": {}}
        derived, records, unresolved = substitute_assigned_pdfs(notebook, Path("/work/course/02_activities"))
        self.assertEqual(notebook["cells"][0]["source"], source)
        self.assertIn("/course/02_activities/documents/managing_oneself.pdf", derived["cells"][0]["source"])
        self.assertEqual(records, [{"cell": 1, "article": "managing_oneself.pdf"}])
        self.assertEqual(unresolved, [])

    def test_ambiguous_pdf_is_not_rewritten(self):
        source = "path = '/Users/ada/managing_oneself-ai_report_2025.pdf'"
        notebook = {"cells": [{"cell_type": "code", "source": source}], "metadata": {}}
        derived, records, unresolved = substitute_assigned_pdfs(notebook, Path("/work/course/02_activities"))
        self.assertEqual(derived["cells"][0]["source"], source)
        self.assertEqual(records, [])
        self.assertEqual(unresolved, [{"cell": 1, "reason": "ambiguous assigned PDF",
                                       "basename": "managing_oneself-ai_report_2025.pdf"}])

    def test_unrelated_local_file_is_not_rewritten(self):
        source = "path = '/Users/ada/private/resume.pdf'"
        notebook = {"cells": [{"cell_type": "code", "source": source}], "metadata": {}}
        derived, records, unresolved = substitute_assigned_pdfs(notebook, Path("/work/course/02_activities"))
        self.assertEqual(derived["cells"][0]["source"], source)
        self.assertEqual(records, [])
        self.assertEqual(unresolved, [])

    def test_existing_course_relative_pdf_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            documents = cwd / "documents"
            documents.mkdir()
            (documents / "managing_oneself.pdf").write_bytes(b"course article")
            source = "path = 'documents/managing_oneself.pdf'"
            notebook = {"cells": [{"cell_type": "code", "source": source}]}
            derived, records, unresolved = substitute_assigned_pdfs(notebook, cwd)
        self.assertEqual(derived["cells"][0]["source"], source)
        self.assertEqual(records, [])
        self.assertEqual(unresolved, [])

    def test_assigned_pdf_web_url_is_not_rewritten(self):
        source = "url = 'https://example.com/ai_report_2025.pdf'"
        notebook = {"cells": [{"cell_type": "code", "source": source}]}
        derived, records, unresolved = substitute_assigned_pdfs(notebook, Path("/work/course/02_activities"))
        self.assertEqual(derived["cells"][0]["source"], source)
        self.assertEqual(records, [])
        self.assertEqual(unresolved, [])


if __name__ == "__main__":
    unittest.main()
