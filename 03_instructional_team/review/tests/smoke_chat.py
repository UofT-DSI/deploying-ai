"""Exercise package and script chat launches in the course image with fake credentials."""

import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import assignment_2_review as assignment_review
import review
from assignment_2_submission import ProjectSnapshot


@contextmanager
def fake_gateway(key):
    assert key == "fake-host-secret"
    yield 1234, "fake-short-token"


def main() -> int:
    issue = review.build_image()
    if issue:
        print(issue)
        return 1
    app = ("import os\n"
           "import gradio as gr\n"
           "def answer(message, history):\n"
           "    return 'gateway=' + str(os.getenv('API_GATEWAY_KEY')) + ' token=' + str(os.getenv('OPENAI_API_KEY'))\n"
           "gr.ChatInterface(answer).launch()\n")
    projects = {
        "script": {"app.py": app.encode()},
        "package": {"__init__.py": b"", "helper.py": b"def value():\n    return 'ready'\n",
                    "app.py": ("from .helper import value\n" + app).encode(),
                    "readme.md": b"Start with python -m assignment_chat.app\n"},
    }
    with patch.object(assignment_review, "notebook_gateway", fake_gateway):
        for kind, files in projects.items():
            snapshot = ProjectSnapshot("synthetic", files, (), "assignment-2")
            result = review.run_project(snapshot, [{"id": "memory_set", "message": "Hello"}],
                                        "fake-host-secret", review.course_image_name(),
                                        review.capture_docker, review.remove_container,
                                        gateway_key="fake-course-secret")
            output = str(result)
            if result["state"] != "observed" or "[REDACTED]" not in output or any(
                    secret in output for secret in ("fake-host-secret", "fake-course-secret", "fake-short-token")):
                print(kind, result)
                return 1
    print("Docker chat smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
