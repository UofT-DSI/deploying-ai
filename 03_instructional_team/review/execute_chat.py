"""Run and probe a submitted chat project inside the review container."""

import importlib.util
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from gradio_client import Client

SOURCE = Path("/input")
PROJECT = Path("/work/project/05_src/assignment_chat")
MAX_EXCHANGES = 12


def startup_file() -> Path | None:
    readme = next((PROJECT / name for name in ("readme.md", "README.md") if (PROJECT / name).is_file()), None)
    if readme:
        text = readme.read_text(encoding="utf-8", errors="replace")[:30000]
        for match in re.finditer(r"(?:python|uv run python)\s+(?:05_src/assignment_chat/|\./)?([\w-]+\.py)\b", text):
            candidate = PROJECT / match.group(1)
            if candidate.is_file():
                return candidate
    return next((PROJECT / name for name in ("app.py", "main.py", "__main__.py")
                 if (PROJECT / name).is_file()), None)


def error_text(log: Path) -> str:
    try:
        data = log.read_bytes()[-4000:].decode("utf-8", "replace")
    except OSError:
        return "App ended without a readable log"
    lines = [line.strip() for line in data.splitlines() if line.strip()]
    return " | ".join(lines[-4:])[:800]


def chat_endpoint(api: dict) -> tuple[str, int] | None:
    endpoints = api.get("named_endpoints", {}) if isinstance(api, dict) else {}
    for name, details in endpoints.items():
        parameters = details.get("parameters", []) if isinstance(details, dict) else []
        if parameters and isinstance(parameters[0], dict) and parameters[0].get("parameter_name") == "message":
            return name, len(parameters)
    return None


def callable_probe(launch: Path, probes: list[dict]) -> dict | None:
    spec = importlib.util.spec_from_file_location("submitted_chat_app", launch)
    if not spec or not spec.loader:
        return None
    sys.path.insert(0, str(PROJECT.parent))
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:  # noqa: BLE001
        return None
    function = next((value for name in ("assignment_chat", "chat", "respond", "reply")
                     if inspect.isfunction(value := getattr(module, name, None))), None)
    if function is None:
        return None
    result = {"state": "observed", "startup": launch.name, "endpoint": f"callable:{function.__name__}",
              "reason": None, "exchanges": []}
    history = []
    for item in probes:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("message"), str):
            continue
        message = item["message"][:1000]
        if item["id"] != "memory_recall":
            history = []
        record = {"id": item["id"][:40], "message": message}
        try:
            reply = function(message, history)
            record["response"] = str(reply)[:4000]
            history.extend(({"role": "user", "content": message},
                            {"role": "assistant", "content": str(reply)[:4000]}))
        except Exception as exc:  # noqa: BLE001
            record["error"] = f"{type(exc).__name__}: {str(exc)[:350]}"
        result["exchanges"].append(record)
    return result


def main() -> None:
    shutil.copytree(SOURCE, PROJECT, dirs_exist_ok=True)
    launch = startup_file()
    if launch is None:
        print(json.dumps({"state": "unavailable", "reason": "No startup script could be inferred from README or project files", "exchanges": []}))
        return
    spec = json.loads(Path("/input/probes.json").read_text(encoding="utf-8"))
    probes = spec[:MAX_EXCHANGES] if isinstance(spec, list) else []
    env = os.environ.copy()
    env["PYTHONPATH"] = "/work/project/05_src:/course/05_src"
    env["GRADIO_SERVER_PORT"] = "7860"
    env["GRADIO_SERVER_NAME"] = "127.0.0.1"
    log = Path("/work/app.log")
    with log.open("wb") as handle:
        app = subprocess.Popen([sys.executable, str(launch)], cwd=PROJECT, env=env,
                               stdout=handle, stderr=subprocess.STDOUT)
    result = {"state": "unavailable", "startup": launch.name, "reason": "App did not expose a reachable Gradio API", "exchanges": []}
    try:
        client = None
        for _ in range(30):
            if app.poll() is not None:
                result["reason"] = "App exited during startup: " + error_text(log)
                break
            try:
                client = Client("http://127.0.0.1:7860", verbose=False)
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        if client is not None:
            try:
                api = client.view_api(print_info=False, return_format="dict")
            except Exception:  # noqa: BLE001
                api = {}
            endpoint = chat_endpoint(api)
            if endpoint is None:
                result["reason"] = "Gradio exposed no chat endpoint; facilitator should inspect the interface"
            else:
                chat_name, parameter_count = endpoint
                result.update({"state": "observed", "reason": None, "endpoint": chat_name})
                history = []
                for item in probes:
                    if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("message"), str):
                        continue
                    message = item["message"][:1000]
                    if item["id"] != "memory_recall":
                        history = []
                    record = {"id": item["id"][:40], "message": message}
                    try:
                        if item["id"] != "memory_recall":
                            client = Client("http://127.0.0.1:7860", verbose=False)
                        arguments = (message, history) if parameter_count >= 2 else (message,)
                        reply = client.predict(*arguments, api_name=chat_name)
                        if isinstance(reply, tuple):
                            reply = reply[0]
                        record["response"] = str(reply)[:4000]
                        history.extend(({"role": "user", "content": message},
                                        {"role": "assistant", "content": str(reply)[:4000]}))
                    except Exception as exc:  # noqa: BLE001
                        record["error"] = f"{type(exc).__name__}: {str(exc)[:200]} | app log: {error_text(log)[:300]}"
                    result["exchanges"].append(record)
        if result["state"] == "unavailable" and app.poll() is not None:
            fallback = callable_probe(launch, probes)
            if fallback is not None:
                result = fallback
    finally:
        app.terminate()
        try:
            app.wait(timeout=5)
        except subprocess.TimeoutExpired:
            app.kill()
            app.wait(timeout=5)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
