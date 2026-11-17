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
    def test_course_helper_change_invalidates_image_tag(self):
        original_read = Path.read_bytes

        def digest_with(content):
            def fake_read(path):
                return content if path.name == "clients.py" else original_read(path)

            review.course_image_name.cache_clear()
            with patch.object(Path, "read_bytes", fake_read):
                return review.course_image_name()

        before = digest_with(b"helper version one")
        after = digest_with(b"helper version two")
        review.course_image_name.cache_clear()
        self.assertNotEqual(before, after)

    def test_build_context_contains_only_trusted_course_helpers(self):
        seen = []

        def fake_run(command, **kwargs):
            seen.append(command[:2])
            if command[:2] == ["docker", "image"]:
                return subprocess.CompletedProcess(command, 1, b"", b"")
            if command[:2] == ["docker", "build"]:
                context = Path(kwargs["cwd"])
                self.assertTrue((context / "05_src/utils/clients.py").is_file())
                self.assertTrue((context / "05_src/utils/logger.py").is_file())
                self.assertFalse((context / "05_src/.secrets").exists())
                self.assertEqual({file.name for file in (context / "02_activities/documents").iterdir()},
                                 {"managing_oneself.pdf", "ai_report_2025.pdf"})
            return subprocess.CompletedProcess(command, 0, b"", b"")

        with patch.object(review.subprocess, "run", side_effect=fake_run):
            self.assertIsNone(review.build_image())
        self.assertIn(["docker", "build"], seen)

    def test_missing_credential_is_environment_block(self):
        with patch.dict(review.os.environ, {}, clear=True), patch.object(review, "build_image") as build:
            self.assertIn("OPENAI_API_KEY", review.prepare_container())
        build.assert_not_called()

    def test_file_resolved_credential_reaches_preflight_and_gateway(self):
        seen = []

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        def fake_urlopen(request, **kwargs):
            seen.append(request.headers["Authorization"])
            return Response()

        with patch.dict(review.os.environ, {}, clear=True), \
             patch.object(review, "build_image", return_value=None), \
             patch.object(review.urllib.request, "urlopen", side_effect=fake_urlopen):
            self.assertIsNone(review.prepare_container("file-key"))
        self.assertEqual(seen, ["Bearer file-key"])

        with patch.object(review, "notebook_gateway", return_value=nullcontext(None)) as gateway, \
             patch.object(review, "capture_docker", return_value=(b'{"cells":[]}', b"", None)):
            review.run_notebook({"cells": []}, "file-key")
        gateway.assert_called_once_with("file-key")

    def test_course_gateway_key_uses_environment_before_secrets_file(self):
        with patch.dict(review.os.environ, {}, clear=True), \
             patch.object(review, "dotenv_values", return_value={"API_GATEWAY_KEY": "file-gateway"}):
            self.assertEqual(review.course_gateway_key(), "file-gateway")
        with patch.dict(review.os.environ, {"API_GATEWAY_KEY": "env-gateway"}), \
             patch.object(review, "dotenv_values") as dotenv:
            self.assertEqual(review.course_gateway_key(), "env-gateway")
        dotenv.assert_not_called()

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

    def test_text_file_is_staged_read_only_for_container_runner(self):
        def fake_capture(command, name):
            mount = command[command.index("--mount") + 1]
            source = Path(mount.split(",")[1].removeprefix("source="))
            self.assertEqual((source / "files/02_activities/documents/source.txt").read_text(), "article")
            self.assertIn("/course/02_activities/documents:rw,nosuid,size=64m", command)
            return b'{"cells":[]}', b"", None

        with patch.object(review, "capture_docker", side_effect=fake_capture):
            _, issue = review.run_notebook({"cells": []}, text_files={"02_activities/documents/source.txt": b"article"})
        self.assertIsNone(issue)

    def test_course_gateway_key_reaches_notebook_without_host_openai_key(self):
        def fake_capture(command, name):
            self.assertIn("API_GATEWAY_KEY=course-key", command)
            self.assertNotIn("OPENAI_API_KEY=host-key", command)
            return b'{"cells":[]}', b"", None

        with patch.object(review, "capture_docker", side_effect=fake_capture):
            _, issue = review.run_notebook({"cells": []}, "host-key", gateway_key="course-key")
        self.assertIsNone(issue)

    def test_course_gateway_key_is_redacted_from_execution_error(self):
        artifact = {"cells": [{"outputs": [{"output_type": "error", "ename": "ValueError",
                                           "evalue": "course-key was rejected"}]}]}
        with patch.object(review, "capture_docker", return_value=(json.dumps(artifact).encode(), b"", None)):
            _, issue = review.run_notebook({"cells": []}, gateway_key="course-key")
        self.assertNotIn("course-key", issue)

    def test_unsafe_text_path_does_not_launch_container(self):
        with patch.object(review, "capture_docker") as capture, self.assertRaisesRegex(ValueError, "unsafe"):
            review.run_notebook({"cells": []}, text_files={"../source.txt": b"article"})
        capture.assert_not_called()

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

    def test_failed_runner_reports_exception_instead_of_cell_source_tail(self):
        stderr = (b"Traceback (most recent call last):\n"
                  b"openai.RateLimitError: request limit reached\n"
                  b"Cell source:\nprint('long notebook source')\n-------------------\n")
        with patch.object(review, "capture_docker", return_value=(b"", stderr, None)):
            executed, issue = review.run_notebook({"cells": []})
        self.assertIsNone(executed)
        self.assertIn("RateLimitError: request limit reached", issue)
        self.assertNotIn("long notebook source", issue)

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

    def test_unrelated_local_file_error_is_student_specific(self):
        artifact = {"cells": [{"outputs": [{"output_type": "error", "ename": "FileNotFoundError",
                                          "evalue": "[Errno 2] No such file: '/Users/ada/private/resume.txt'"}]}]}
        with patch.object(review, "capture_docker", return_value=(json.dumps(artifact).encode(), b"", None)):
            _, issue = review.run_notebook({"cells": []})
        self.assertEqual(issue, "Student: code cell 1 raised FileNotFoundError for an unrelated local file")

    def test_invalid_api_request_is_student_specific(self):
        artifact = {"cells": [{"outputs": [{"output_type": "error", "ename": "BadRequestError",
                                          "evalue": "Error code: 400 - invalid request parameters"}]}]}
        with patch.object(review, "capture_docker", return_value=(json.dumps(artifact).encode(), b"", None)):
            _, issue = review.run_notebook({"cells": []})
        self.assertEqual(issue, "Student: code cell 1 raised Error code: 400 - invalid request parameters")

    def test_gateway_model_rejection_names_policy(self):
        artifact = {"cells": [{"outputs": [{"output_type": "error", "ename": "PermissionDeniedError",
                                           "evalue": "Error code: 403 - {'error': 'model not permitted'}"}]}]}
        with patch.object(review, "capture_docker", return_value=(json.dumps(artifact).encode(), b"", None)):
            _, issue = review.run_notebook({"cells": []})
        self.assertIn("outside the evaluator gateway policy", issue)

    def test_missing_trusted_course_helper_file_is_pending(self):
        artifact = {"cells": [{"outputs": [{"output_type": "error", "ename": "FileNotFoundError",
                                          "evalue": "No such file: '/course/05_src/utils/clients.py'"}]}]}
        with patch.object(review, "capture_docker", return_value=(json.dumps(artifact).encode(), b"", None)):
            _, issue = review.run_notebook({"cells": []})
        self.assertEqual(issue, "Environment: code cell 1 could not access a trusted course file")

    def test_ambiguous_assigned_pdf_error_is_pending(self):
        artifact = {"metadata": {"assignment_review": {"unresolved": [
            {"cell": 1, "reason": "ambiguous assigned PDF", "basename": "article.pdf"}]}},
            "cells": [{"outputs": [{"output_type": "error", "ename": "FileNotFoundError",
                                    "evalue": "No such file: '/Users/ada/article.pdf'"}]}]}
        with patch.object(review, "capture_docker", return_value=(json.dumps(artifact).encode(), b"", None)):
            _, issue = review.run_notebook({"cells": []})
        self.assertEqual(issue, "Environment: code cell 1 has an ambiguous assigned PDF reference")

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
