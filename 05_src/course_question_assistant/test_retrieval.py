import unittest

from course_question_assistant.retrieval import load_passages, retrieve_passages


class RetrievalTests(unittest.TestCase):
    def test_finds_embedding_retrieval_lesson(self):
        passages = retrieve_passages("How does embedding-based retrieval work?")
        self.assertTrue(passages)
        self.assertTrue(any(p.file == "05_rag.md" and "Embedding" in p.heading for p in passages))

    def test_unrelated_question_does_not_match(self):
        self.assertEqual([], retrieve_passages("How can attention improve my romantic relationship?"))

    def test_finds_system_evaluation_with_common_verb_form(self):
        passages = retrieve_passages("Why evaluate a whole AI system?")
        self.assertTrue(any(p.file == "03_evaluation.md" for p in passages))

    def test_follow_up_uses_recent_topic(self):
        history = [
            {"role": "user", "content": "How does embedding retrieval work?"},
            {"role": "assistant", "content": "It matches semantic meaning."},
        ]
        passages = retrieve_passages("How does it compare with keyword search?", history)
        self.assertTrue(any(p.file == "05_rag.md" for p in passages))

    def test_presentation_markup_is_not_a_passage(self):
        passages = load_passages()
        self.assertTrue(passages)
        self.assertFalse(any(p.heading in {"Main Points", "Agenda", "References"} for p in passages))
        self.assertFalse(any("marp: true" in p.text or "![" in p.text for p in passages))


if __name__ == "__main__":
    unittest.main()
