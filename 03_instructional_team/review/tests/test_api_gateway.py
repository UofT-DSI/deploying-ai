import http.client
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch


script = Path(__file__).resolve().parents[1] / "api_gateway.py"
spec = importlib.util.spec_from_file_location("assignment_gateway", script)
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


class GatewayTests(unittest.TestCase):
    def test_only_bounded_permitted_calls_reach_upstream_with_real_key(self):
        seen = []

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, size):
                return b'{"choices":[]}'

        def fake_upstream(request, **kwargs):
            seen.append(request)
            return Response()

        with patch.object(gateway.urllib.request, "urlopen", side_effect=fake_upstream):
            with gateway.notebook_gateway("real-secret") as (port, token):
                conn = http.client.HTTPConnection("127.0.0.1", port)
                body = json.dumps({"model": "gpt-4o-mini", "messages": [], "max_completion_tokens": 5000})
                conn.request("POST", "/v1/chat/completions", body,
                             {"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                response.read()
                conn.request("POST", "/v1/chat/completions", body,
                             {"Authorization": "Bearer wrong", "Content-Type": "application/json"})
                self.assertEqual(conn.getresponse().status, 403)
                conn.close()
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].headers["Authorization"], "Bearer real-secret")
        self.assertEqual(json.loads(seen[0].data)["max_completion_tokens"], 512)


if __name__ == "__main__":
    unittest.main()
