import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "execute_chat.py"
spec = importlib.util.spec_from_file_location("execute_chat_adapter", module_path)
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)


class ChatEndpointTests(unittest.TestCase):
    def test_callback_name_can_differ_from_chat(self):
        api = {"named_endpoints": {"/status": {"parameters": []},
                                   "/reply": {"parameters": [{"parameter_name": "message"}]}}}
        self.assertEqual(adapter.chat_endpoint(api), ("/reply", 1))

    def test_legacy_history_parameter(self):
        api = {"named_endpoints": {"/respond": {"parameters": [{"parameter_name": "message"},
                                                                {"parameter_name": "history"}]}}}
        self.assertEqual(adapter.chat_endpoint(api), ("/respond", 2))

    def test_package_launch_for_relative_import_and_script_launch(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "assignment_chat"
            project.mkdir()
            (project / "__init__.py").write_text("", encoding="utf-8")
            app = project / "app.py"
            app.write_text("from .helper import respond\n", encoding="utf-8")
            with patch.object(adapter, "PROJECT", project):
                command, cwd = adapter.launch_command(app)
                self.assertEqual(command[1:], ["-m", "assignment_chat.app"])
                self.assertEqual(cwd, project.parent)
                app.write_text("print('hello')\n", encoding="utf-8")
                command, cwd = adapter.launch_command(app)
                self.assertEqual(command[1:], [str(app)])
                self.assertEqual(cwd, project)
                (project / "readme.md").write_text("Start with python -m assignment_chat.app\n", encoding="utf-8")
                self.assertEqual(adapter.startup_file(), app)
                command, cwd = adapter.launch_command(app)
                self.assertEqual(command[1:], ["-m", "assignment_chat.app"])


if __name__ == "__main__":
    unittest.main()
