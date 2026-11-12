"""Find student assignment pull requests and create local review reports."""

import argparse
import csv
import hashlib
import json
import logging
import re
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
    pr_number: int | None = None
    missing: tuple[str, ...] = ()
    row_number: int | None = None
    issue: str | None = None


class Result(NamedTuple):
    kind: str
    primary: dict | None = None
    state: str | None = None
    reason: str | None = None


class LookupFailure(Exception):
    """The supplied PR could not be verified."""


def parse_pr_url(url: str) -> tuple[str, int, str]:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if (parsed.scheme != "https" or parsed.netloc.lower() != "github.com"
            or parsed.query or parsed.fragment or parsed.params or len(parts) != 4
            or parts[2] != "pull" or not parts[3].isdigit() or int(parts[3]) < 1):
        raise ValueError(f"invalid GitHub pull request URL: {url}")
    owner, repo_name = parts[:2]
    if not re.fullmatch(r"[A-Za-z0-9-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", repo_name):
        raise ValueError(f"invalid GitHub pull request URL: {url}")
    repo = f"{owner}/{repo_name}"
    number = int(parts[3])
    return repo, number, f"https://github.com/{repo}/pull/{number}"


def make_student(name: str, email: str, url: str) -> Student:
    name, email, url = name.strip(), email.strip(), url.strip()
    if not name or not email or not url or "@" not in email:
        raise ValueError("name, email, and GitHub pull request URL are required")
    if any(ord(char) < 32 for char in name + email + url):
        raise ValueError("student fields cannot contain control characters")
    repo, number, canonical_url = parse_pr_url(url)
    return Student(name, email, canonical_url, repo, number)


def parse_input(argv: list[str] | None = None) -> tuple[list[Student], tuple[int, ...], Path]:
    parser = argparse.ArgumentParser(
        description="Verify supplied assignment PR links and create local Markdown review reports. Run from the repository base directory.",
        epilog="Example: python 03_instructional_team/review/review.py --student 'Ada Lovelace' ada@example.com https://github.com/ada/deploying-ai/pull/42 --assignment 1",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--student", nargs=3, action="append", metavar=("NAME", "EMAIL", "PR_URL"), help="Student details; repeat for more students")
    source.add_argument("--csv", type=Path, help="CSV with name,email,repo_url columns; repo_url contains the PR link")
    parser.add_argument("--assignment", required=True, choices=("1", "2"), help="Assignment to check")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORTS, help="Parent directory for a new report run")
    args = parser.parse_args(argv)

    if args.student:
        students = [make_student(*row) for row in args.student]
    else:
        try:
            with args.csv.open(newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    raise ValueError("CSV needs a header row")
                students = []
                for row_number, row in enumerate(reader, start=2):
                    name = (row.get("name") or "").strip()
                    email = (row.get("email") or "").strip()
                    url = (row.get("repo_url") or "").strip()
                    missing = tuple(key for key, value in (("name", name), ("email", email), ("repo_url", url)) if not value)
                    if missing:
                        issue = f"Missing input: {', '.join(missing)}"
                        logging.warning("CSV row %s: %s; skipping lookup", row_number, issue)
                        students.append(Student(name, email, url, "", missing=missing, row_number=row_number, issue=issue))
                        continue
                    try:
                        students.append(make_student(name, email, url))
                    except ValueError as exc:
                        logging.warning("CSV row %s: %s; skipping lookup", row_number, exc)
                        students.append(Student(name, email, url, "", row_number=row_number, issue=str(exc)))
        except OSError as exc:
            raise ValueError(f"cannot read CSV: {exc}") from exc
        if not students:
            raise ValueError("CSV contains no students")
    assignments = (int(args.assignment),)
    return students, assignments, args.output_dir


def fetch_pr(repo: str, number: int) -> dict:
    endpoint = f"repos/{repo}/pulls/{number}"
    try:
        completed = subprocess.run(
            ["gh", "api", "--method", "GET", endpoint],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
    except (OSError, UnicodeError) as exc:
        raise LookupFailure(f"GitHub CLI could not run: {exc}") from exc
    if completed.returncode:
        detail = completed.stderr.strip().splitlines()
        raise LookupFailure(detail[0] if detail else f"GitHub CLI exited with code {completed.returncode}")
    try:
        pr = json.loads(completed.stdout)
        if not isinstance(pr, dict) or pr.get("number") != number:
            raise ValueError("unexpected response shape")
        return pr
    except (ValueError, TypeError) as exc:
        raise LookupFailure(f"GitHub returned invalid PR data: {exc}") from exc


def select_pr(pr: dict, assignment: int) -> Result:
    branch = ASSIGNMENT_BRANCH[assignment]
    actual = (pr.get("head") or {}).get("ref")
    if actual != branch:
        return Result("warning", primary=pr, reason=f"PR branch {actual or 'unknown'} does not match {branch}")
    state = "merged" if pr.get("merged_at") else pr.get("state", "unknown")
    return Result("found", pr, state=state)


def report_text(student: Student, assignment: int, result: Result) -> str:
    lines = [
        f"# Assignment {assignment} review: {student.name or f'CSV row {student.row_number}'}", "",
        f"- Student: {student.name or 'Missing'}",
        f"- Email: {student.email or 'Missing'}",
        f"- Repository: {f'https://github.com/{student.repo}' if student.repo else 'Unknown'}",
        f"- Supplied PR URL: {student.url or 'Missing'}",
        f"- Assignment: {assignment}",
    ]
    if result.kind == "found":
        lines.extend(["- Status: Found", f"- PR: {result.primary['html_url']}", f"- PR status: {result.state}"])
        if result.state == "closed":
            lines.append("- Note: This PR is closed.")
        elif result.state == "merged":
            lines.append("- Note: This PR was closed by merging.")
    elif result.kind == "warning":
        lines.extend(["- Status: Warning", "", result.reason or "Input needs review."])
    else:
        lines.extend(["- Status: Error", "", f"Verification could not be completed: {result.reason}"])
    lines.extend(["", "## Grade", "", "Grading pending.", ""])
    return "\n".join(lines)


def write_reports(items: list[tuple[Student, int, Result]], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=output_dir))
    paths = []
    for index, (student, assignment, result) in enumerate(items, start=1):
        digest = hashlib.sha256(student.email.casefold().encode("utf-8")).hexdigest()[:10]
        repo_slug = student.repo.replace("/", "-").lower() or f"row-{student.row_number}"
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
    items = []
    cache = {}
    for student in students:
        if student.issue:
            for assignment in assignments:
                items.append((student, assignment, Result("warning", reason=student.issue)))
            continue
        if student.url not in cache:
            try:
                cache[student.url] = fetch_pr(student.repo, student.pr_number)
            except LookupFailure as exc:
                cache[student.url] = exc
        for assignment in assignments:
            found = cache[student.url]
            result = Result("unverifiable", reason=str(found)) if isinstance(found, LookupFailure) else select_pr(found, assignment)
            items.append((student, assignment, result))
    try:
        paths = write_reports(items, output_dir)
    except OSError as exc:
        print(f"Could not write reports: {exc}")
        return 2
    counts = {kind: sum(result.kind == kind for _, _, result in items) for kind in ("found", "warning", "unverifiable")}
    print(f"Reports: {len(paths)} (found: {counts['found']}, warnings: {counts['warning']}, errors: {counts['unverifiable']})")
    for path in paths:
        print(path)
    return 0 if not counts["warning"] and not counts["unverifiable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
