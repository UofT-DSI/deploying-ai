import json
from pathlib import Path

_LAST_PATH_FILE = Path(__file__).resolve().parent / "last_path.json"


def load_last_path() -> str:
    if not _LAST_PATH_FILE.exists():
        return ""
    try:
        return json.loads(_LAST_PATH_FILE.read_text(encoding="utf-8")).get("path", "")
    except Exception:
        return ""


def save_last_path(path: str) -> None:
    _LAST_PATH_FILE.write_text(json.dumps({"path": path}), encoding="utf-8")
