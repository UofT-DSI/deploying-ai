import unittest
from unittest.mock import patch

from course_question_assistant.app import course_chat


class ChatTests(unittest.TestCase):
    @patch("course_question_assistant.app.get_model")
    def test_answer_shows_cited_slide(self, get_model):
        get_model.return_value.invoke.return_value.content = "Embeddings match semantic meaning [1]."
        answer = course_chat("How does embedding-based retrieval work?", [])
        self.assertIn("Embeddings match semantic meaning [1].", answer)
        self.assertIn("05_rag.md", answer)
        self.assertIn("Embedding-Based Retrieval", answer)

    @patch("course_question_assistant.app.get_model")
    def test_unsupported_question_does_not_call_model(self, get_model):
        answer = course_chat("How can attention improve my romantic relationship?", [])
        self.assertIn("couldn't find support", answer.lower())
        get_model.assert_not_called()

    @patch("course_question_assistant.app.get_model")
    def test_uncited_model_answer_is_not_presented_as_grounded(self, get_model):
        get_model.return_value.invoke.return_value.content = "Embeddings are vectors."
        answer = course_chat("How does embedding-based retrieval work?", [])
        self.assertIn("couldn't verify", answer.lower())


if __name__ == "__main__":
    unittest.main()
