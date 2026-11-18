import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

module_path = Path(__file__).resolve().parents[1] / "assignment_2_review.py"
sys.path.insert(0, str(module_path.parent))
spec = importlib.util.spec_from_file_location("assignment_2_review", module_path)
review = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = review
spec.loader.exec_module(review)


class Assignment2ReviewTests(unittest.TestCase):
    def test_rubric_caps_sum_to_one_hundred(self):
        self.assertEqual(sum(cap for _, _, cap, _ in review.RUBRIC), 100)
        self.assertEqual(len({id_ for id_, _, _, _ in review.RUBRIC}), len(review.RUBRIC))

    def test_positive_score_needs_exact_citation(self):
        entries = (review.Evidence("source:app.py:1", "1: response = api.get(url)"),)
        raw = {"scores": [{"id": id_, "points": 0, "reason": "No evidence", "citations": [], "pending": False}
                          for id_, _, _, _ in review.RUBRIC]}
        raw["scores"][0].update(points=5, citations=[{"id": "source:app.py:1", "excerpt": "api.get(url)"}])
        scores = review._validate(raw, entries)
        self.assertEqual(scores[0].points, 5)
        raw["scores"][0]["citations"][0]["excerpt"] = "api.post(url)"
        with self.assertRaisesRegex(ValueError, "unsupported citation"):
            review._validate(raw, entries)

    def test_missing_service_probe_makes_service_pending(self):
        scores = tuple(review.Score(id_, 1, "Source supports partial credit", (("source:app.py:1", "api"),))
                       for id_, _, _, _ in review.RUBRIC)
        runtime = {"state": "observed", "exchanges": [{"id": "memory_set", "response": "Okay"},
                                                     {"id": "memory_recall", "response": "indigo"}]}
        resolved = {item.id: item for item in review.reconcile(scores, scores, runtime)}
        self.assertTrue(resolved["api_service"].pending)
        self.assertFalse(resolved["memory"].pending)

    def test_blocked_behavior_cannot_receive_full_points(self):
        scores = tuple(review.Score(id_, cap, "Source implementation", (("source:app.py:1", "api"),))
                       for id_, _, cap, _ in review.RUBRIC)
        resolved = {item.id: item for item in review.reconcile(scores, scores, {"state": "unavailable", "exchanges": []})}
        self.assertEqual(resolved["api_service"].points, 5)
        self.assertTrue(resolved["api_service"].pending)
        self.assertEqual(resolved["semantic_data"].points, 8)

    def test_runtime_award_requires_probe_citation(self):
        scores = tuple(review.Score(id_, cap, "Source claim", (("source:app.py:1", "api"),))
                       for id_, _, cap, _ in review.RUBRIC)
        runtime = {"state": "observed", "exchanges": [{"id": "service_api", "response": "fine"}]}
        resolved = {item.id: item for item in review.reconcile(scores, scores, runtime)}
        self.assertEqual(resolved["api_service"].points, 5)
        self.assertTrue(resolved["api_service"].pending)

    def test_thresholds_and_pending(self):
        self.assertEqual(review.label(59, False), "Incomplete")
        self.assertEqual(review.label(60, False), "Complete")
        self.assertEqual(review.label(24, False), "Missing")
        self.assertEqual(review.label(60, True), "Pending")

    def test_container_receives_gateway_token_without_real_key(self):
        snapshot = review.ProjectSnapshot("sha", {"app.py": b"print('hello')"}, (), "assignment-2")
        commands = []

        def capture(command, name, timeout):
            commands.append(command)
            return b'{"state":"unavailable","reason":"ephemeral-token","exchanges":[]}', b"", None

        from contextlib import contextmanager

        @contextmanager
        def gateway(key):
            self.assertEqual(key, "real-secret")
            yield 1234, "ephemeral-token"

        with patch.object(review, "notebook_gateway", gateway):
            result = review.run_project(snapshot, [], "real-secret", "course-image", capture, lambda name: None)
        command_text = " ".join(commands[0])
        self.assertIn("OPENAI_API_KEY=ephemeral-token", command_text)
        self.assertNotIn("real-secret", command_text)
        self.assertEqual(result["reason"], "[REDACTED]")

    def test_report_uses_resolved_scores_and_redacts_secret(self):
        scores = tuple(review.Score(id_, cap, "Observed evidence real-secret", (("probe:test", "worked"),))
                       for id_, _, cap, _ in review.RUBRIC)
        text = review.report(None, {"state": "observed", "exchanges": []}, scores, None,
                             "Ada", "https://example.test/pr/1", "real-secret")
        self.assertIn("Proposed score: 100 / 100", text)
        self.assertIn("## Encouraging observations", text)
        self.assertNotIn("real-secret", text)

    def test_mechanical_pass_retains_source_credit_when_runtime_blocked(self):
        snapshot = review.ProjectSnapshot("sha", {"readme.md": b"# My chat\n", "app.py": b"chat = gr.ChatInterface(fn)\n",
                                                  "search.py": b"db = chromadb.PersistentClient(path='index')\n",
                                                  "index/chroma.sqlite3": b"internal index"}, (), "assignment-2")
        runtime = {"state": "unavailable", "reason": "API outage", "exchanges": []}
        evidence = review.source_evidence(snapshot, None) + review.runtime_evidence(runtime, None)
        scores = {item.id: item for item in review.mechanical_pass(evidence, runtime)}
        self.assertEqual(scores["chat_ui"].points, 2)
        self.assertEqual(scores["explanation"].points, 1)
        self.assertEqual(scores["semantic_data"].points, 2)
        self.assertTrue(scores["chat_ui"].pending)

    def test_ai_pass_uses_strict_schema_and_validates_scores(self):
        entries = (review.Evidence("source:app.py:1", "1: api.get(url)"),)
        payload = {"scores": [{"id": id_, "points": 0, "reason": "No supporting evidence", "citations": [], "pending": True}
                              for id_, _, _, _ in review.RUBRIC]}

        class Responses:
            def create(self, **kwargs):
                self.kwargs = kwargs
                return type("Response", (), {"status": "completed", "output_text": json.dumps(payload)})()

        client = type("Client", (), {"responses": Responses()})()
        scores, issue = review.ai_pass(entries, None, client=client)
        self.assertIsNone(issue)
        self.assertEqual(len(scores), 13)
        self.assertFalse(client.responses.kwargs["store"])
        self.assertTrue(client.responses.kwargs["text"]["format"]["strict"])

    def test_incomplete_and_invalid_passes_are_named_in_pending_report(self):
        entries = (review.Evidence("source:app.py:1", "1: api.get(url)"),)
        class Responses:
            def __init__(self, status, output):
                self.status, self.output = status, output

            def create(self, **kwargs):
                return type("Response", (), {"status": self.status, "output_text": self.output})()

        incomplete = type("Client", (), {"responses": Responses("incomplete", "")})()
        _, reason = review.ai_pass(entries, None, client=incomplete)
        self.assertIn("Incomplete model response", reason)
        invalid = type("Client", (), {"responses": Responses("completed", '{"scores":[]}')})()
        _, invalid_reason = review.ai_pass(entries, None, client=invalid)
        self.assertIn("Invalid review output", invalid_reason)
        baseline = review.mechanical_pass(entries + (review.Evidence("runtime:status", "Docker unavailable"),),
                                          {"state": "unavailable", "exchanges": []})
        text = review.report(None, {"state": "unavailable", "reason": "Docker unavailable", "exchanges": []},
                             baseline, invalid_reason, "Ada", "https://example.test/pull/1", None,
                             pass_issues={"Independent AI": invalid_reason})
        self.assertIn("at least 0 / 100", text)
        self.assertIn("Independent AI: Invalid review output", text)
        self.assertNotIn("Provisional score-based classification", text)
        self.assertNotIn("Missing", text)

    def test_fallback_cites_three_service_modules_and_next_checks(self):
        snapshot = review.ProjectSnapshot("sha", {
            "api.py": b"answer = requests.get(url)\n",
            "search.py": b"matches = store.similarity_search(question)\n",
            "third.py": b"result = client.web_search(query)\n",
        }, (), "assignment-2")
        runtime = {"state": "unavailable", "reason": "Course dependency unavailable", "exchanges": []}
        evidence = review.source_evidence(snapshot, None) + review.runtime_evidence(runtime, None)
        scores = {item.id: item for item in review.mechanical_pass(evidence, runtime)}
        for id_, path in (("api_service", "api.py"), ("semantic_query", "search.py"),
                          ("third_tool", "third.py")):
            self.assertGreater(scores[id_].points, 0)
            self.assertIn(path, scores[id_].citations[0][0])
            self.assertIn("Next check:", scores[id_].reason)
            self.assertTrue(scores[id_].pending)

    def test_readme_example_is_not_service_implementation_credit(self):
        snapshot = review.ProjectSnapshot("sha", {
            "readme.md": b"Example: requests.get(url) and gr.ChatInterface(fn)\n",
        }, (), "assignment-2")
        runtime = {"state": "unavailable", "reason": "No app", "exchanges": []}
        evidence = review.source_evidence(snapshot, None) + review.runtime_evidence(runtime, None)
        scores = {item.id: item for item in review.mechanical_pass(evidence, runtime)}
        self.assertEqual(scores["api_service"].points, 0)
        self.assertEqual(scores["chat_ui"].points, 0)

    def test_gateway_secret_is_redacted_from_runner_and_report(self):
        snapshot = review.ProjectSnapshot("sha", {"app.py": b"print('hello')"}, (), "assignment-2")
        commands = []

        def capture(command, name, timeout):
            commands.append(command)
            return b'{"state":"unavailable","reason":"limited-secret","exchanges":[]}', b"", None

        from contextlib import contextmanager
        @contextmanager
        def gateway(key):
            yield 1234, "short-token"

        with patch.object(review, "notebook_gateway", gateway):
            result = review.run_project(snapshot, [], "host-secret", "image", capture, lambda name: None,
                                        gateway_key="limited-secret")
        self.assertIn("API_GATEWAY_KEY=limited-secret", commands[0])
        self.assertNotIn("host-secret", commands[0])
        self.assertEqual(result["reason"], "[REDACTED]")
        text = review.report(snapshot, result, review.mechanical_pass(review.runtime_evidence(result, None), result),
                             "host-secret limited-secret", "Ada", "url", "host-secret", gateway_key="limited-secret")
        self.assertNotIn("host-secret", text)
        self.assertNotIn("limited-secret", text)


if __name__ == "__main__":
    unittest.main()
