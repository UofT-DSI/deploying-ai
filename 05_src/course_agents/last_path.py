import json
from pathlib import Path
from utils.logger import get_logger

_logs = get_logger(__name__)
_LAST_PATH_FILE = Path(__file__).resolve().parent / "last_path.json"

DEFAULT_A1 = r"02_activities\assignment_1.ipynb"
DEFAULT_A2 = r"05_src\assignment_chat"


def load_last_paths() -> tuple[str, str]:
    """Return (a1_path, a2_path) from saved state, or defaults."""
    if not _LAST_PATH_FILE.exists():
        _logs.debug("load_last_paths: file not found, using defaults")
        return DEFAULT_A1, DEFAULT_A2
    try:
        data = json.loads(_LAST_PATH_FILE.read_text(encoding="utf-8"))
        a1 = data.get("a1_path", DEFAULT_A1)
        a2 = data.get("a2_path", DEFAULT_A2)
        _logs.debug("load_last_paths: loaded a1=%s a2=%s", a1, a2)
        return a1, a2
    except Exception as exc:
        _logs.warning("load_last_paths: failed to read %s, using defaults: %s", _LAST_PATH_FILE, exc)
        return DEFAULT_A1, DEFAULT_A2


def save_last_paths(a1_path: str, a2_path: str) -> None:
    _logs.debug("save_last_paths: writing a1=%s a2=%s", a1_path, a2_path)
    _LAST_PATH_FILE.write_text(
        json.dumps({"a1_path": a1_path, "a2_path": a2_path}),
        encoding="utf-8",
    )
    _logs.info("save_last_paths: saved to %s", _LAST_PATH_FILE)
