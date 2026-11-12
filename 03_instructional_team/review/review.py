"""Find student assignment pull requests and create one CSV review report."""

import argparse
import csv
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
REPORT_FIELDS = ("input_row", "student_name", "email", "repo_url", "repository_url", "assignment", "status", "pr_url", "pr_state", "missing_items", "note")
ASSIGNMENT_TITLE = re.compile(r"\bassignment[\s#:_-]*0*([12])\b", re.IGNORECASE)


class Student(NamedTuple):
    name: str
    email: str
    url: str
    repo: str
    missing: tuple[str, ...] = ()
    row_number: int | None = None
    issue: str | None = None


class Result(NamedTuple):
    kind: str
    primary: dict | None = None
    state: str | None = None
    reason: str | None = None


class LookupFailure(Exception):
    """The repository's PR list could not be verified."""


def parse_listing_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if (parsed.scheme != "https" or parsed.netloc.lower() != "github.com"
            or parsed.params or len(parts) != 3 or parts[2] not in ("pull", "pulls")):
        raise ValueError(f"invalid GitHub pull request listing URL: {url}")
    owner, repo_name = parts[:2]
    if not re.fullmatch(r"[A-Za-z0-9-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", repo_name):
        raise ValueError(f"invalid GitHub pull request listing URL: {url}")
    repo = f"{owner}/{repo_name}"
    return repo, f"https://github.com/{repo}/pulls"


def make_student(name: str, email: str, url: str) -> Student:
    name, email, url = name.strip(), email.strip(), url.strip()
    if not name or not email or not url or "@" not in email:
        raise ValueError("name, email, and GitHub pull request listing URL are required")
    if any(ord(char) < 32 for char in name + email + url):
        raise ValueError("student fields cannot contain control characters")
    repo, canonical_url = parse_listing_url(url)
    return Student(name, email, canonical_url, repo)


def parse_input(argv: list[str] | None = None) -> tuple[list[Student], tuple[int, ...], Path]:
    parser = argparse.ArgumentParser(
        description="Find assignment PRs from repository PR listing links and create one CSV report. Run from the repository base directory.",
        epilog="Example: python 03_instructional_team/review/review.py --student 'Ada Lovelace' ada@example.com https://github.com/ada/deploying-ai/pulls --assignment 1",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--student", nargs=3, action="append", metavar=("NAME", "EMAIL", "PULLS_URL"), help="Student details; repeat for more students")
    source.add_argument("--csv", type=Path, help="CSV with name,email,repo_url columns; repo_url contains the PR listing link")
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
                        students.append(make_student(name, email, url)._replace(row_number=row_number))
                    except ValueError as exc:
                        logging.warning("CSV row %s: %s; skipping lookup", row_number, exc)
                        students.append(Student(name, email, url, "", row_number=row_number, issue=str(exc)))
        except OSError as exc:
            raise ValueError(f"cannot read CSV: {exc}") from exc
        if not students:
            raise ValueError("CSV contains no students")
    assignments = (int(args.assignment),)
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
    matches = []
    for pr in prs:
        title_match = ASSIGNMENT_TITLE.search(pr.get("title") or "")
        if title_match:
            belongs = int(title_match.group(1)) == assignment
        else:
            belongs = (pr.get("head") or {}).get("ref") == branch
        if belongs:
            matches.append(pr)
    if not matches:
        return Result("not_submitted")
    pr = max(matches, key=lambda candidate: (candidate.get("created_at") or "", candidate.get("number") or 0))
    state = "merged" if pr.get("merged_at") else pr.get("state", "unknown")
    return Result("submitted", pr, state=state)


def report_row(student: Student, assignment: int, result: Result) -> dict[str, str | int]:
    note = result.reason or ""
    if result.kind == "submitted" and result.state in ("closed", "merged"):
        note = "PR is closed" if result.state == "closed" else "PR was closed by merging"
    return {
        "input_row": student.row_number or "",
        "student_name": student.name,
        "email": student.email,
        "repo_url": student.url,
        "repository_url": f"https://github.com/{student.repo}" if student.repo else "",
        "assignment": assignment,
        "status": "error" if result.kind == "unverifiable" else result.kind,
        "pr_url": result.primary.get("html_url", "") if result.primary else "",
        "pr_state": result.state or "",
        "missing_items": ", ".join(student.missing),
        "note": note,
    }


def write_report(items: list[tuple[Student, int, Result]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    assignment = items[0][1]
    with tempfile.NamedTemporaryFile(mode="w", newline="", encoding="utf-8", prefix=f"assignment-{assignment}-review-", suffix=".csv", dir=output_dir, delete=False) as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(report_row(student, number, result) for student, number, result in items)
        return Path(handle.name)


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
        path = write_report(items, output_dir)
    except OSError as exc:
        print(f"Could not write reports: {exc}")
        return 2
    counts = {kind: sum(result.kind == kind for _, _, result in items) for kind in ("submitted", "not_submitted", "warning", "unverifiable")}
    print(f"Students: {len(items)} (submitted: {counts['submitted']}, not submitted: {counts['not_submitted']}, warnings: {counts['warning']}, errors: {counts['unverifiable']})")
    print(path)
    return 0 if not counts["warning"] and not counts["unverifiable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
