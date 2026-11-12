"""Find student assignment pull requests and create local review reports."""

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse


DEFAULT_REPORTS = Path("03_instructional_team/review/reports")
ASSIGNMENT_BRANCH = {1: "assignment-1", 2: "assignment-2"}


class Student(NamedTuple):
    name: str
    email: str
    url: str
    repo: str


class Result(NamedTuple):
    kind: str
    primary: dict | None = None
    other: list[dict] | None = None
    state: str | None = None
    reason: str | None = None


class LookupFailure(Exception):
    """The repository's PRs could not be verified."""


def make_student(name: str, email: str, url: str) -> Student:
    name, email, url = name.strip(), email.strip(), url.strip()
    if not name or not email or not url or "@" not in email:
        raise ValueError("name, email, and GitHub repository URL are required")
    if any(ord(char) < 32 for char in name + email + url):
        raise ValueError("student fields cannot contain control characters")
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if (parsed.scheme != "https" or parsed.netloc.lower() != "github.com"
            or parsed.query or parsed.fragment or parsed.params or len(parts) != 2):
        raise ValueError(f"invalid GitHub repository URL: {url}")
    owner, repo_name = parts
    repo_name = repo_name.removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", repo_name):
        raise ValueError(f"invalid GitHub repository URL: {url}")
    repo = f"{owner}/{repo_name}"
    return Student(name, email, f"https://github.com/{repo}", repo)


def parse_input(argv: list[str] | None = None) -> tuple[list[Student], tuple[int, ...], Path]:
    parser = argparse.ArgumentParser(
        description="Find assignment PRs and create local Markdown review reports. Run from the repository base directory.",
        epilog="Example: python 03_instructional_team/review/review.py --student 'Ada Lovelace' ada@example.com https://github.com/ada/deploying-ai --assignment both",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--student", nargs=3, action="append", metavar=("NAME", "EMAIL", "REPO_URL"), help="Student details; repeat for more students")
    source.add_argument("--csv", type=Path, help="CSV with name,email,repo_url columns")
    parser.add_argument("--assignment", required=True, choices=("1", "2", "both"), help="Assignment to check")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORTS, help="Parent directory for a new report run")
    args = parser.parse_args(argv)

    if args.student:
        students = [make_student(*row) for row in args.student]
    else:
        try:
            with args.csv.open(newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames or not {"name", "email", "repo_url"}.issubset(reader.fieldnames):
                    raise ValueError("CSV must have name,email,repo_url columns")
                students = []
                for row_number, row in enumerate(reader, start=2):
                    try:
                        students.append(make_student(row.get("name") or "", row.get("email") or "", row.get("repo_url") or ""))
                    except ValueError as exc:
                        raise ValueError(f"CSV row {row_number}: {exc}") from exc
        except OSError as exc:
            raise ValueError(f"cannot read CSV: {exc}") from exc
        if not students:
            raise ValueError("CSV contains no students")
    assignments = (1, 2) if args.assignment == "both" else (int(args.assignment),)
    return students, assignments, args.output_dir


def fetch_prs(repo: str) -> list[dict]:
    endpoint = f"repos/{repo}/pulls?state=all&per_page=100"
    try:
        completed = subprocess.run(
            ["gh", "api", "--method", "GET", "--paginate", "--slurp", endpoint],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
    except (OSError, UnicodeError) as exc:
        raise LookupFailure(f"GitHub CLI could not run: {exc}") from exc
    if completed.returncode:
        detail = completed.stderr.strip().splitlines()
        raise LookupFailure(detail[0] if detail else f"GitHub CLI exited with code {completed.returncode}")
    try:
        pages = json.loads(completed.stdout)
        if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
            raise ValueError("unexpected response shape")
        return [pr for page in pages for pr in page]
    except (ValueError, TypeError) as exc:
        raise LookupFailure(f"GitHub returned invalid PR data: {exc}") from exc


def select_pr(prs: list[dict], assignment: int) -> Result:
    branch = ASSIGNMENT_BRANCH[assignment]
    matches = [pr for pr in prs if pr.get("head", {}).get("ref") == branch]
    if not matches:
        return Result("absent")
    matches.sort(key=lambda pr: (pr.get("created_at", ""), pr.get("number", 0)), reverse=True)
    primary = matches[0]
    state = "merged" if primary.get("merged_at") else primary.get("state", "unknown")
    return Result("found", primary, matches[1:], state)


def report_text(student: Student, assignment: int, result: Result) -> str:
    lines = [
        f"# Assignment {assignment} review: {student.name}", "",
        f"- Student: {student.name}",
        f"- Email: {student.email}",
        f"- Repository: {student.url}",
        f"- Assignment: {assignment}",
    ]
    if result.kind == "found":
        lines.extend([f"- Primary PR: {result.primary['html_url']}", f"- PR status: {result.state}"])
        if result.state == "closed":
            lines.append("- Note: This PR is closed.")
        elif result.state == "merged":
            lines.append("- Note: This PR was closed by merging.")
        if result.other:
            lines.extend(["", "## Other matching PRs", ""])
            lines.extend(f"- {pr['html_url']}" for pr in result.other)
    elif result.kind == "absent":
        lines.extend(["", "No matching submission PR was found."])
    else:
        lines.extend(["", f"Verification could not be completed: {result.reason}"])
    lines.extend(["", "## Grade", "", "Grading pending.", ""])
    return "\n".join(lines)


def write_reports(items: list[tuple[Student, int, Result]], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=output_dir))
    paths = []
    for index, (student, assignment, result) in enumerate(items, start=1):
        digest = hashlib.sha256(student.email.casefold().encode("utf-8")).hexdigest()[:10]
        repo_slug = student.repo.replace("/", "-").lower()
        path = run_dir / f"{index:04d}-{repo_slug}-{digest}-assignment-{assignment}.md"
        path.write_text(report_text(student, assignment, result), encoding="utf-8")
        paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> int:
    try:
        students, assignments, output_dir = parse_input(argv)
    except ValueError as exc:
        print(f"Input error: {exc}")
        return 2
    if shutil.which("gh") is None:
        print("GitHub CLI (gh) is required. Install it and run 'gh auth login'.")
        return 2
    items = []
    cache = {}
    for student in students:
        if student.repo not in cache:
            try:
                cache[student.repo] = fetch_prs(student.repo)
            except LookupFailure as exc:
                cache[student.repo] = exc
        for assignment in assignments:
            found = cache[student.repo]
            result = Result("unverifiable", reason=str(found)) if isinstance(found, LookupFailure) else select_pr(found, assignment)
            items.append((student, assignment, result))
    try:
        paths = write_reports(items, output_dir)
    except OSError as exc:
        print(f"Could not write reports: {exc}")
        return 2
    counts = {kind: sum(result.kind == kind for _, _, result in items) for kind in ("found", "absent", "unverifiable")}
    print(f"Reports: {len(paths)} (found: {counts['found']}, absent: {counts['absent']}, unverifiable: {counts['unverifiable']})")
    for path in paths:
        print(path)
    return 0 if not counts["unverifiable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
