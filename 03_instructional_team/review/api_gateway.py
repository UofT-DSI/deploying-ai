"""Short-lived, bounded OpenAI access for an untrusted notebook container."""

import json
import secrets
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_REQUEST_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_REQUESTS = 20
ALLOWED_PATHS = {"/v1/chat/completions", "/v1/responses", "/v1/embeddings"}
ALLOWED_MODELS = {"gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "gpt-5.4", "text-embedding-3-small"}


@contextmanager
def notebook_gateway(api_key: str | None):
    if not api_key:
        yield None
        return

    token = secrets.token_urlsafe(24)
    remaining = MAX_REQUESTS
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, code: int, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            nonlocal remaining
            if self.path not in ALLOWED_PATHS or self.headers.get("Authorization") != f"Bearer {token}":
                self.respond(403, b'{"error":"request not permitted"}')
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if not 0 < length <= MAX_REQUEST_BYTES:
                self.respond(413, b'{"error":"request too large"}')
                return
            with lock:
                if remaining <= 0:
                    self.respond(429, b'{"error":"run request limit reached"}')
                    return
                remaining -= 1
            try:
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict) or payload.get("model") not in ALLOWED_MODELS:
                    self.respond(403, b'{"error":"model not permitted"}')
                    return
                if self.path == "/v1/chat/completions":
                    limit_field = "max_tokens" if "max_tokens" in payload else "max_completion_tokens"
                    payload[limit_field] = min(int(payload.get(limit_field, 512)), 512)
                elif self.path == "/v1/responses":
                    payload["max_output_tokens"] = min(int(payload.get("max_output_tokens", 512)), 512)
                body = json.dumps(payload).encode("utf-8")
                request = urllib.request.Request(
                    "https://api.openai.com" + self.path,
                    data=body,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(request, timeout=45) as response:
                        result = response.read(MAX_RESPONSE_BYTES + 1)
                        status = response.status
                except urllib.error.HTTPError as exc:
                    result = exc.read(MAX_RESPONSE_BYTES + 1)
                    status = exc.code
                if len(result) > MAX_RESPONSE_BYTES:
                    self.respond(502, b'{"error":"upstream response too large"}')
                else:
                    self.respond(status, result)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                self.respond(502, b'{"error":"API request unavailable"}')

    server = ThreadingHTTPServer(("0.0.0.0", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, token
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
