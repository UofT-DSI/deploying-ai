"""Fetch a bounded Assignment 2 project from one pull-request commit."""

import base64
import binascii
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath

PROJECT_PREFIX = "05_src/assignment_chat/"
MAX_FILES = 500
MAX_FILE_BYTES = 40 * 1024 * 1024
MAX_PROJECT_BYTES = 80 * 1024 * 1024
SKIPPED_NAMES = {".secrets", ".env", "__pycache__"}


class ProjectUnavailable(Exception):
    """The selected PR or its project files could not be verified."""


class ProjectMissing(Exception):
    """The selected commit has no Assignment 2 project."""


@dataclass(frozen=True)
class ProjectSnapshot:
    sha: str
    files: dict[str, bytes]
    changed_paths: tuple[str, ...]
    branch: str


def _project_path(path: object) -> str | None:
    if (not isinstance(path, str) or not path.startswith(PROJECT_PREFIX)
            or "\\" in path or re.search(r"[\x00-\x1f:]", path)):
        return None
    relative = path[len(PROJECT_PREFIX):]
    raw_parts = relative.split("/")
    parts = PurePosixPath(relative).parts
    if (not parts or any(part in ("", ".", "..") for part in raw_parts)
            or any(part in SKIPPED_NAMES or part.startswith((".env", ".secrets")) for part in parts)):
        return None
    return relative


def fetch_project_snapshot(repo: str, pr: dict, api: Callable) -> ProjectSnapshot:
    head = pr.get("head") or {}
    sha = head.get("sha")
    number = pr.get("number")
    head_repo = (head.get("repo") or {}).get("full_name")
    if not isinstance(sha, str) or not sha or not isinstance(number, int) or not head_repo:
        raise ProjectUnavailable("PR head commit or repository is unavailable")
    commit = api(f"repos/{head_repo}/git/commits/{sha}")
    tree_sha = (commit.get("tree") or {}).get("sha") if isinstance(commit, dict) else None
    if not tree_sha:
        raise ProjectUnavailable("PR commit tree is unavailable")
    tree = api(f"repos/{head_repo}/git/trees/{tree_sha}?recursive=1")
    if not isinstance(tree, dict) or tree.get("truncated") or not isinstance(tree.get("tree"), list):
        raise ProjectUnavailable("PR project tree is unavailable or truncated")
    entries = []
    total = 0
    for entry in tree["tree"]:
        if not isinstance(entry, dict):
            raise ProjectUnavailable("PR project tree has an invalid entry")
        path = _project_path(entry.get("path"))
        if path is None:
            continue
        if entry.get("type") == "tree":
            continue
        if entry.get("type") != "blob" or entry.get("mode") not in ("100644", "100755"):
            raise ProjectUnavailable(f"Unsupported project entry: {path}")
        size = entry.get("size")
        if not isinstance(size, int) or size < 0 or size > MAX_FILE_BYTES:
            raise ProjectUnavailable(f"Project file exceeds review limit: {path}")
        total += size
        if total > MAX_PROJECT_BYTES or len(entries) >= MAX_FILES:
            raise ProjectUnavailable("Project exceeds review size or file-count limit")
        entries.append((path, entry.get("sha"), size))
    if not entries:
        raise ProjectMissing("Assignment 2 project is absent from the PR head commit")
    files = {}
    for path, blob_sha, size in entries:
        blob = api(f"repos/{head_repo}/git/blobs/{blob_sha}")
        if not isinstance(blob, dict) or blob.get("encoding") != "base64" or not isinstance(blob.get("content"), str):
            raise ProjectUnavailable(f"Project file is unavailable: {path}")
        try:
            raw = base64.b64decode(re.sub(r"\s", "", blob["content"]), validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ProjectUnavailable(f"Project file is invalid: {path}") from exc
        if len(raw) != size:
            raise ProjectUnavailable(f"Project file size changed: {path}")
        if path in files:
            raise ProjectUnavailable(f"Duplicate project file: {path}")
        files[path] = raw
    changed = api(f"repos/{repo}/pulls/{number}/files?per_page=100", paginate=True)
    current = api(f"repos/{repo}/pulls/{number}")
    if not isinstance(changed, list) or any(not isinstance(item, dict) or "filename" not in item for item in changed):
        raise ProjectUnavailable("PR file list is unavailable")
    if not isinstance(current, dict) or (current.get("head") or {}).get("sha") != sha:
        raise ProjectUnavailable("PR head changed while retrieving its project")
    return ProjectSnapshot(sha, files, tuple(item["filename"] for item in changed), head.get("ref") or "")
