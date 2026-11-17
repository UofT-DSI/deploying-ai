"""Fetch bounded text inputs from an Assignment 1 PR head."""

import base64
import binascii
import re
from collections.abc import Callable

MAX_TEXT_FILES = 100
MAX_TEXT_FILE_BYTES = 1024 * 1024
MAX_TEXT_BYTES = 8 * 1024 * 1024
PRIVATE_NAME = re.compile(r"(?:^|[._-])(?:secrets?|credentials?|tokens?|passwords?|api[_-]?keys?)(?:$|[._-])", re.IGNORECASE)
PRIVATE_CONTENT = re.compile(
    rb"(?:[A-Z0-9_]*(?:API[_-]?KEY|[_-]KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)[A-Z0-9_]*\s*=|sk-[A-Za-z0-9_-]{8,})",
    re.IGNORECASE,
)


def eligible_text_path(path: object) -> bool:
    if not isinstance(path, str) or not path.lower().endswith(".txt") or "\\" in path:
        return False
    parts = path.split("/")
    return bool(parts) and parts[:2] != ["05_src", "utils"] and all(
        part not in ("", ".", "..") and not part.lower().startswith((".env", ".secrets"))
        and not PRIVATE_NAME.search(part) and not re.search(r"[\x00-\x1f:]", part)
        for part in parts
    )


def fetch_text_files(head_repo: str, sha: str, api: Callable) -> dict[str, bytes]:
    commit = api(f"repos/{head_repo}/git/commits/{sha}")
    tree_sha = (commit.get("tree") or {}).get("sha") if isinstance(commit, dict) else None
    if not tree_sha:
        raise ValueError("PR commit tree is unavailable")
    tree = api(f"repos/{head_repo}/git/trees/{tree_sha}?recursive=1")
    if not isinstance(tree, dict) or tree.get("truncated") or not isinstance(tree.get("tree"), list):
        raise ValueError("PR text-file tree is unavailable or truncated")
    entries = []
    total = 0
    for entry in tree["tree"]:
        if not isinstance(entry, dict):
            raise TypeError("PR text-file tree has an invalid entry")
        path = entry.get("path")
        if not eligible_text_path(path):
            continue
        if entry.get("type") != "blob" or entry.get("mode") not in ("100644", "100755"):
            raise ValueError(f"Unsupported text-file entry: {path}")
        size = entry.get("size")
        if not isinstance(size, int) or size < 0 or size > MAX_TEXT_FILE_BYTES:
            raise ValueError(f"Text file exceeds review limit: {path}")
        total += size
        if total > MAX_TEXT_BYTES or len(entries) >= MAX_TEXT_FILES:
            raise ValueError("Submission text exceeds review size or file-count limit")
        entries.append((path, entry.get("sha"), size))
    files = {}
    for path, blob_sha, size in entries:
        blob = api(f"repos/{head_repo}/git/blobs/{blob_sha}")
        if not isinstance(blob, dict) or blob.get("encoding") != "base64" or not isinstance(blob.get("content"), str):
            raise ValueError(f"Text file is unavailable: {path}")
        try:
            raw = base64.b64decode(re.sub(r"\s", "", blob["content"]), validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError(f"Text file is invalid: {path}") from exc
        if len(raw) != size:
            raise ValueError(f"Text file size changed: {path}")
        if not PRIVATE_CONTENT.search(raw):
            files[path] = raw
    return files
