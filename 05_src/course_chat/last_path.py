import json
from pathlib import Path

_LAST_PATH_FILE = Path(__file__).resolve().parent / "last_path.json"

DEFAULT_A1 = r"02_activities\assignment_1.ipynb"
DEFAULT_A2 = r"05_src\assignment_chat"


def load_last_paths() -> tuple[str, str]:
    """Return (a1_path, a2_path) from saved state, or defaults."""
    if not _LAST_PATH_FILE.exists():
        return DEFAULT_A1, DEFAULT_A2
    try:
        data = json.loads(_LAST_PATH_FILE.read_text(encoding="utf-8"))
        return data.get("a1_path", DEFAULT_A1), data.get("a2_path", DEFAULT_A2)
    except Exception:
        return DEFAULT_A1, DEFAULT_A2


def save_last_paths(a1_path: str, a2_path: str) -> None:
    _LAST_PATH_FILE.write_text(
        json.dumps({"a1_path": a1_path, "a2_path": a2_path}),
        encoding="utf-8",
    )
