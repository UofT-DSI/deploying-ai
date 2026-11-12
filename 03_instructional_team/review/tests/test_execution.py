import importlib.util
import json
import subprocess
import unittest
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

    def test_container_receives_only_assignment_credential_and_returns_output(self):
        notebook = {"cells": [{"cell_type": "code", "source": ["print('fixture')"]}]}
        seen = []

        def fake_run(command, **kwargs):
            seen.append(command)
            self.assertEqual(command[:2], ["docker", "run"])
            self.assertIn("--read-only", command)
            self.assertIn("--pids-limit", command)
            self.assertEqual([command[i + 1] for i, value in enumerate(command[:-1]) if value == "--env"],
                             ["OPENAI_API_KEY", "HOME=/tmp", "IPYTHONDIR=/tmp/ipython"])
            mount = command[command.index("--mount") + 1]
            folder = Path(mount.split(",target=")[0].removeprefix("type=bind,source="))
            (folder / "executed.ipynb").write_text(json.dumps({"cells": [{"outputs": [{"text": "fixture"}]}]}), encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch.object(review.subprocess, "run", side_effect=fake_run):
            executed, issue = review.run_notebook(notebook)
        self.assertIsNone(issue)
        self.assertEqual(executed["cells"][0]["outputs"][0]["text"], "fixture")
        self.assertEqual(len(seen), 1)

    def test_timeout_removes_container(self):
        def fake_run(command, **kwargs):
            if command[:2] == ["docker", "run"]:
                raise subprocess.TimeoutExpired(command, 900)
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch.object(review.subprocess, "run", side_effect=fake_run) as run:
            executed, issue = review.run_notebook({"cells": []})
        self.assertIsNone(executed)
        self.assertIn("timed out", issue)
        self.assertEqual(run.call_args_list[-1].args[0][:3], ["docker", "rm", "-f"])

    def test_interrupt_removes_container(self):
        def fake_run(command, **kwargs):
            if command[:2] == ["docker", "run"]:
                raise KeyboardInterrupt
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch.object(review.subprocess, "run", side_effect=fake_run) as run:
            with self.assertRaises(KeyboardInterrupt):
                review.run_notebook({"cells": []})
        self.assertEqual(run.call_args_list[-1].args[0][:3], ["docker", "rm", "-f"])

    def test_service_error_is_distinguished_from_student_error(self):
        def execute_with(error_name):
            def fake_run(command, **kwargs):
                mount = command[command.index("--mount") + 1]
                folder = Path(mount.split(",target=")[0].removeprefix("type=bind,source="))
                (folder / "executed.ipynb").write_text(json.dumps({"cells": [{"outputs": [
                    {"output_type": "error", "ename": error_name, "evalue": error_name}]}]}), encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, "", "")
            with patch.object(review.subprocess, "run", side_effect=fake_run):
                return review.run_notebook({"cells": []})[1]

        self.assertIn("Environment:", execute_with("APIConnectionError"))
        self.assertIn("Student:", execute_with("NameError"))
        self.assertIn("Environment:", execute_with("ModuleNotFoundError"))
        self.assertIn("Environment:", execute_with("HTTPError"))


if __name__ == "__main__":
    unittest.main()
