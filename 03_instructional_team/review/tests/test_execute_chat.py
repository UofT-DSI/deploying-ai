import importlib.util
import sys
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


if __name__ == "__main__":
    unittest.main()
