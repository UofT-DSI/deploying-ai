import importlib.util
import io
import json
import subprocess
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

script = Path(__file__).resolve().parents[1] / "review.py"
spec = importlib.util.spec_from_file_location("assignment_review_execution", script)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ExecutionTests(unittest.TestCase):
    def test_missing_credential_is_environment_block(self):
        with patch.dict(review.os.environ, {}, clear=True), patch.object(review, "build_image") as build:
            self.assertIn("OPENAI_API_KEY", review.prepare_container())
        build.assert_not_called()

    def test_container_uses_read_only_input_and_proxy_token(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["print('fixture')"]}]}
        executed = {"cells": [{"outputs": [{"output_type": "stream", "text": "fixture"}]}]}
        seen = []

        def fake_capture(command, name):
            seen.append(command)
            self.assertEqual(command[:2], ["docker", "run"])
            self.assertIn("--read-only", command)
            self.assertIn("/work:rw,nosuid,size=512m", command)
            self.assertIn("readonly", command[command.index("--mount") + 1])
            self.assertNotIn("real-secret", " ".join(command))
            self.assertIn("OPENAI_API_KEY=proxy-token", command)
            return json.dumps(executed).encode(), b"", None

        with patch.dict(review.os.environ, {"OPENAI_API_KEY": "real-secret"}), \
             patch.object(review, "notebook_gateway", return_value=nullcontext((8844, "proxy-token"))), \
             patch.object(review, "capture_docker", side_effect=fake_capture):
            result, issue = review.run_notebook(notebook)
        self.assertIsNone(issue)
        self.assertEqual(result, executed)
        self.assertEqual(len(seen), 1)

    def test_malformed_executed_cell_is_unavailable_evidence(self):
        artifacts = (
            {"cells": [None]},
            {"cells": [{"outputs": [None]}]},
            {"cells": [{"outputs": [{"output_type": "display_data", "data": "bad"}]}]},
            {"cells": [{"outputs": [{"output_type": "stream", "text": ["ok", 7]}]}]},
            {"cells": [{"outputs": [{"output_type": "display_data", "data": {"text/markdown": ["Score: 1", 7]}}]}]},
        )
        for artifact in artifacts:
            with self.subTest(artifact=artifact), patch.object(
                review, "capture_docker", return_value=(json.dumps(artifact).encode(), b"", None)
            ):
                executed, issue = review.run_notebook({"cells": []})
            self.assertIsNone(executed)
            self.assertIn("unavailable", issue.lower())

    def test_executed_markdown_cell_needs_no_outputs_field(self):
        artifact = {"cells": [{"cell_type": "markdown", "source": "instructions"},
                              {"cell_type": "code", "outputs": []}]}
        with patch.object(review, "capture_docker", return_value=(json.dumps(artifact).encode(), b"", None)):
            executed, issue = review.run_notebook({"cells": []})
        self.assertIsNone(issue)
        self.assertEqual(executed, artifact)

    def test_later_service_error_is_not_hidden_by_name_error(self):
        artifact = {"cells": [
            {"outputs": [{"output_type": "error", "ename": "NameError", "evalue": "missing"}]},
            {"outputs": [{"output_type": "error", "ename": "APIConnectionError", "evalue": "offline"}]},
        ]}
        with patch.object(review, "capture_docker", return_value=(json.dumps(artifact).encode(), b"", None)):
            _, issue = review.run_notebook({"cells": []})
        self.assertTrue(issue.startswith("Environment:"))

    def test_service_error_is_distinguished_from_student_error(self):
        for name, prefix in (("APIConnectionError", "Environment:"), ("NameError", "Student:"),
                             ("ModuleNotFoundError", "Environment:"), ("HTTPError", "Environment:")):
            artifact = {"cells": [{"outputs": [{"output_type": "error", "ename": name, "evalue": name}]}]}
            with self.subTest(name=name), patch.object(review, "capture_docker", return_value=(json.dumps(artifact).encode(), b"", None)):
                self.assertTrue(review.run_notebook({"cells": []})[1].startswith(prefix))

    def test_timeout_removes_container(self):
        process = self.fake_process()
        process.wait = lambda **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("docker", 900))
        with patch.object(review.subprocess, "Popen", return_value=process), \
             patch.object(review, "remove_container") as remove:
            output, _, issue = review.capture_docker(["docker", "run"], "test-container")
        self.assertIsNone(output)
        self.assertIn("timed out", issue)
        self.assertTrue(process.killed)
        remove.assert_called_once_with("test-container")

    def test_output_over_limit_is_not_returned_to_grader(self):
        process = self.fake_process()
        process.stdout = io.BytesIO(b"oversized output")
        with patch.object(review.subprocess, "Popen", return_value=process), \
             patch.object(review, "MAX_NOTEBOOK_RESULT", 8), \
             patch.object(review, "remove_container") as remove:
            output, _, issue = review.capture_docker(["docker", "run"], "test-container")
        self.assertIsNone(output)
        self.assertIn("exceeded limit", issue)
        self.assertTrue(process.killed)
        remove.assert_called_once_with("test-container")

    def test_interrupt_removes_container(self):
        process = self.fake_process()
        process.wait = lambda **kwargs: (_ for _ in ()).throw(KeyboardInterrupt())
        with patch.object(review.subprocess, "Popen", return_value=process), \
             patch.object(review, "remove_container") as remove, \
             self.assertRaises(KeyboardInterrupt):
            review.capture_docker(["docker", "run"], "test-container")
        self.assertTrue(process.killed)
        remove.assert_called_once_with("test-container")

    @staticmethod
    def fake_process():
        class Process:
            stdout = io.BytesIO()
            stderr = io.BytesIO()
            killed = False

            def wait(self, **kwargs):
                return 0

            def kill(self):
                self.killed = True

        return Process()


if __name__ == "__main__":
    unittest.main()
