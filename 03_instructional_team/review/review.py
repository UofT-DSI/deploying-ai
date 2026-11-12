"""Find student assignment pull requests and create one CSV review report."""

import argparse
import base64
import binascii
import csv
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assignment_1_rubric import assess, grade_label


DEFAULT_REPORTS = Path("03_instructional_team/review/reports")
COURSE_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def course_image_name() -> str:
    digest = hashlib.sha256()
    files = [COURSE_ROOT / "pyproject.toml", COURSE_ROOT / "uv.lock",
             Path(__file__).with_name("Dockerfile")]
    files.extend(sorted((COURSE_ROOT / "02_activities" / "documents").glob("*.pdf")))
    for source in files:
        digest.update(str(source.relative_to(COURSE_ROOT)).encode("utf-8"))
        digest.update(source.read_bytes())
    return "assignment-1-evaluator:" + digest.hexdigest()[:16]


ASSIGNMENT_BRANCH = {1: "assignment-1", 2: "assignment-2"}
REPORT_FIELDS = ("input_row", "student_name", "email", "repo_url", "repository_url", "assignment", "status", "pr_url", "pr_state", "missing_items", "note")
ASSIGNMENT_TITLE = re.compile(r"\bassignment[\s#:_-]*(?:0*([12])|(one|two))\b", re.IGNORECASE)


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


class AssignmentSnapshot(NamedTuple):
    sha: str
    notebook: dict
    changed_paths: tuple[str, ...]
    branch: str


class LookupFailure(Exception):
    """The repository's PR list could not be verified."""


class NotebookMissing(Exception):
    """The submitted PR does not contain the assigned notebook."""


def github_api(endpoint: str, paginate: bool = False):
    command = ["gh", "api", "--method", "GET"]
    if paginate:
        command.extend(("--paginate", "--slurp"))
    command.append(endpoint)
    try:
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    except (OSError, UnicodeError) as exc:
        raise LookupFailure(f"GitHub CLI could not run: {exc}") from exc
    if completed.returncode:
        detail = completed.stderr.strip().splitlines()
        raise LookupFailure(detail[0] if detail else f"GitHub CLI exited with code {completed.returncode}")
    try:
        data = json.loads(completed.stdout)
        if paginate:
            if not isinstance(data, list) or any(not isinstance(page, list) for page in data):
                raise ValueError("unexpected paginated response shape")
            return [item for page in data for item in page]
        return data
    except (ValueError, TypeError) as exc:
        raise LookupFailure(f"GitHub returned invalid data: {exc}") from exc


def fetch_assignment_snapshot(repo: str, pr: dict) -> AssignmentSnapshot:
    head = pr.get("head") or {}
    sha = head.get("sha")
    number = pr.get("number")
    if not sha or not number:
        raise LookupFailure("PR has no head commit or number")
    head_repo = (head.get("repo") or {}).get("full_name")
    if not head_repo:
        raise LookupFailure("PR head repository is unavailable; cannot verify its notebook")
    endpoint = f"repos/{head_repo}/contents/02_activities/assignment_1.ipynb?ref={sha}"
    try:
        payload = github_api(endpoint)
    except LookupFailure as exc:
        if "404" in str(exc):
            raise NotebookMissing("Assigned notebook is absent from the PR head commit") from exc
        raise
    try:
        if payload["encoding"] != "base64":
            raise ValueError("unexpected content encoding")
        notebook = json.loads(base64.b64decode(payload["content"], validate=True))
        if (not isinstance(notebook, dict) or not isinstance(notebook.get("cells"), list)
                or any(not isinstance(cell, dict) or not isinstance(cell.get("source", ""), (str, list))
                       or (isinstance(cell.get("source"), list) and any(not isinstance(line, str) for line in cell["source"]))
                       for cell in notebook["cells"])):
            raise ValueError("invalid notebook shape")
    except (KeyError, ValueError, TypeError, UnicodeError, binascii.Error) as exc:
        raise NotebookMissing(f"Assigned notebook is invalid: {exc}") from exc
    files = github_api(f"repos/{repo}/pulls/{number}/files?per_page=100", paginate=True)
    current = github_api(f"repos/{repo}/pulls/{number}")
    if not isinstance(files, list) or any(not isinstance(item, dict) or "filename" not in item for item in files):
        raise LookupFailure("GitHub returned an invalid PR file list")
    if not isinstance(current, dict):
        raise LookupFailure("GitHub returned invalid PR metadata")
    if (current.get("head") or {}).get("sha") != sha:
        raise LookupFailure("PR head changed while retrieving its notebook; rerun to use a consistent snapshot")
    return AssignmentSnapshot(sha, notebook, tuple(item["filename"] for item in files), head.get("ref") or "")


def redact(value: str) -> str:
    secret = os.environ.get("OPENAI_API_KEY")
    return value.replace(secret, "[REDACTED]") if secret else value


def build_image() -> str | None:
    try:
        info = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=15, check=False)
        if info.returncode:
            return "Docker daemon is unavailable: " + redact(info.stderr.strip()[:300])
        cached = subprocess.run(["docker", "image", "inspect", course_image_name()], capture_output=True, timeout=15, check=False)
        if cached.returncode == 0:
            return None
        with tempfile.TemporaryDirectory(prefix="assignment-image-") as tmp:
            context = Path(tmp)
            shutil.copy2(COURSE_ROOT / "pyproject.toml", context / "pyproject.toml")
            shutil.copy2(COURSE_ROOT / "uv.lock", context / "uv.lock")
            review_dir = context / "03_instructional_team" / "review"
            review_dir.mkdir(parents=True)
            shutil.copy2(Path(__file__).with_name("Dockerfile"), review_dir / "Dockerfile")
            shutil.copy2(Path(__file__).with_name("execute_notebook.py"), review_dir / "execute_notebook.py")
            documents = context / "02_activities" / "documents"
            documents.mkdir(parents=True)
            for source in (COURSE_ROOT / "02_activities" / "documents").glob("*.pdf"):
                shutil.copy2(source, documents / source.name)
            build = subprocess.run(["docker", "build", "-f", "03_instructional_team/review/Dockerfile", "-t", course_image_name(), "."],
                                   cwd=context, capture_output=True, text=True, timeout=1800, check=False)
        if build.returncode:
            return "Course image build failed: " + redact(build.stderr.strip()[-2500:])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "Evaluator setup failed: " + redact(str(exc))
    return None


def prepare_container() -> str | None:
    if not os.environ.get("OPENAI_API_KEY"):
        return "OPENAI_API_KEY is unavailable to the evaluator"
    build_issue = build_image()
    if build_issue:
        return build_issue
    try:
        probe = subprocess.run(["docker", "run", "--rm", "--env", "OPENAI_API_KEY", course_image_name(), "python", "-c",
                                "import os,urllib.request; r=urllib.request.Request('https://api.openai.com/v1/models', headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']}); urllib.request.urlopen(r,timeout=15).close()"],
                               capture_output=True, text=True, timeout=45, check=False)
        if probe.returncode:
            return "OpenAI service preflight failed: " + redact(probe.stderr.strip()[-400:])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "OpenAI service preflight failed: " + redact(str(exc))
    return None


def run_notebook(notebook: dict) -> tuple[dict | None, str | None]:
    name = "assignment-review-" + uuid.uuid4().hex[:12]
    def remove_container() -> None:
        try:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=20, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass

    with tempfile.TemporaryDirectory(prefix="assignment-review-") as tmp:
        folder = Path(tmp)
        (folder / "notebook.ipynb").write_text(json.dumps(notebook), encoding="utf-8")
        shutil.copy2(Path(__file__).with_name("execute_notebook.py"), folder / "execute_notebook.py")
        documents = folder / "documents"
        documents.mkdir()
        for source in (COURSE_ROOT / "02_activities" / "documents").glob("*.pdf"):
            shutil.copy2(source, documents / source.name)
        command = ["docker", "run", "--rm", "--name", name, "--read-only", "--tmpfs", "/tmp:rw,nosuid,size=512m",
                   "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "128", "--memory", "4g", "--cpus", "2",
                   "--env", "OPENAI_API_KEY", "--env", "HOME=/tmp", "--env", "IPYTHONDIR=/tmp/ipython",
                   "--mount", f"type=bind,source={folder.resolve()},target=/course/02_activities/submission",
                   course_image_name(), "python", "/course/02_activities/submission/execute_notebook.py", "/course/02_activities/submission/notebook.ipynb",
                   "/course/02_activities/submission/executed.ipynb"]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=900, check=False)
        except subprocess.TimeoutExpired:
            remove_container()
            return None, "Notebook execution timed out; facilitator review required"
        except KeyboardInterrupt:
            remove_container()
            raise
        except OSError as exc:
            return None, f"Docker execution failed: {redact(str(exc))}"
        output = folder / "executed.ipynb"
        if output.exists():
            try:
                executed = json.loads(output.read_text(encoding="utf-8"))
                errors = [(i, item) for i, cell in enumerate(executed.get("cells", []), 1)
                          for item in cell.get("outputs", []) if item.get("output_type") == "error"]
                if errors:
                    cell, error = errors[0]
                    message = redact(str(error.get("evalue") or error.get("ename") or "unknown error"))
                    error_name = str(error.get("ename", ""))
                    student_error = error_name in {
                        "NameError", "SyntaxError", "IndentationError", "TypeError", "AttributeError",
                        "IndexError", "KeyError", "ZeroDivisionError", "AssertionError", "UnboundLocalError",
                    }
                    prefix = "Student" if student_error else "Environment"
                    return executed, f"{prefix}: code cell {cell} raised {clean_error(message)}"
                return executed, None
            except (OSError, ValueError):
                pass
        return None, "Notebook execution unavailable: " + redact(completed.stderr.strip()[-400:])


def clean_error(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ")[:300]


def parse_listing_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if (parsed.scheme != "https" or parsed.netloc.lower() not in ("github.com", "www.github.com")
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
        students = []
        for row_number, (name, email, url) in enumerate(args.student, 1):
            missing = tuple(key for key, value in (("name", name), ("email", email), ("repo_url", url)) if not value.strip())
            if missing:
                students.append(Student(name, email, url, "", missing=missing, row_number=row_number,
                                        issue=f"Missing input: {', '.join(missing)}"))
            else:
                try:
                    students.append(make_student(name, email, url)._replace(row_number=row_number))
                except ValueError as exc:
                    students.append(Student(name, email, url, "", row_number=row_number, issue=str(exc)))
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
    prs = github_api(endpoint, paginate=True)
    if any(not isinstance(pr, dict) for pr in prs):
        raise LookupFailure("GitHub returned invalid PR data")
    return prs


def select_pr(prs: list[dict], assignment: int) -> Result:
    branch = ASSIGNMENT_BRANCH[assignment]
    matches = []
    for pr in prs:
        title_match = ASSIGNMENT_TITLE.search(pr.get("title") or "")
        if title_match:
            found_assignment = int(title_match.group(1)) if title_match.group(1) else {"one": 1, "two": 2}[title_match.group(2).lower()]
            belongs = found_assignment == assignment
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


def write_assignment_report(path: Path, student: Student, result: Result,
                            snapshot: AssignmentSnapshot | None, criteria: tuple | None,
                            execution_note: str | None) -> None:
    def clean(value: object) -> str:
        return redact(str(value or "")).replace("|", "\\|").replace("\r", " ").replace("\n", " ")

    lines = ["# Assignment 1 — Draft assessment", "", f"- Student: {clean(student.name) or 'Unknown'}",
             f"- Email: {clean(student.email) or 'Missing'}",
             f"- Repository: https://github.com/{clean(student.repo)}" if student.repo else "- Repository: Unavailable",
             f"- PR: {clean((result.primary or {}).get('html_url')) or 'Unavailable'}",
             f"- PR state: {clean(result.state) or 'Unavailable'}",
             f"- PR head commit: {clean(snapshot.sha) if snapshot else 'Unavailable'}", ""]
    if not criteria:
        lines.extend(["## Assessment unavailable", "", clean(result.reason or result.kind), "",
                      "Facilitator: resolve the submission or intake issue before assigning a grade.", ""])
    else:
        points = sum(item.earned for item in criteria)
        pending = any(item.pending for item in criteria)
        label = grade_label(points, pending)
        percentage = "Percentage: pending until all rubric parts are assessed." if pending else f"Draft percentage: {points:g}%."
        lines.extend([f"## Overall: {label} (draft)", "", f"Assessed points: {points:g} / 100.", percentage,
                      "Facilitator confirmation is required before this is a final grade.", "",
                      "## Rubric", "", "| Criterion | Earned / available | Evidence and feedback |", "| --- | ---: | --- |"])
        for item in criteria:
            details = "; ".join(f"{part.label}: {'Pending' if part.pending else f'{part.earned:g}'}/{part.available:g} — {clean(part.evidence)}" for part in item.parts)
            row_score = f"{item.earned:g} / {item.available:g}" + (" assessed; pending parts excluded" if item.pending else "")
            lines.append(f"| {item.name}{' (review)' if item.pending else ''} | {row_score} | {details} |")
        passed = [(item.name, part) for item in criteria for part in item.parts if part.earned > 0]
        missed = [(item.name, part) for item in criteria for part in item.parts if not part.pending and part.earned < part.available]
        lines.extend(["", "## Encouraging observations", ""])
        lines.extend(f"- {name}: {part.label} ({clean(part.evidence)})." for name, part in passed[:5])
        if not passed:
            lines.append("- No supported rubric work was detected; review the notebook before confirming this draft.")
        lines.extend(["", "## Specific improvements", ""])
        lines.extend(f"- {name}: demonstrate {part.label.lower()} and show the result in the notebook." for name, part in missed)
        if not missed:
            lines.append("- No scored gaps were identified; confirm the provisional judgments against the source article.")
        if execution_note:
            lines.extend(["", "## Execution note", "", clean(execution_note)])
        lines.extend(["", "## Submission format (outside points)", "",
                      f"- Branch: {clean(snapshot.branch) if snapshot else 'Unavailable'}" + (" (expected assignment-1)" if snapshot and snapshot.branch != "assignment-1" else ""),
                      "- Changes only assigned notebook: " + ("Yes" if snapshot and snapshot.changed_paths == ("02_activities/assignment_1.ipynb",) else "No"),
                      "- Changed files: " + (", ".join(clean(path) for path in snapshot.changed_paths) if snapshot else "Unavailable"), ""])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    assessments = []
    if assignments == (1,):
        setup_checked = False
        setup_issue = None
        updated_items = []
        for student, assignment, result in items:
            snapshot = None
            criteria = None
            execution_note = None
            if result.kind == "submitted":
                try:
                    snapshot = fetch_assignment_snapshot(student.repo, result.primary)
                    if not setup_checked:
                        setup_issue = prepare_container()
                        setup_checked = True
                    if setup_issue:
                        executed, execution_note = None, setup_issue
                    else:
                        try:
                            executed, execution_note = run_notebook(snapshot.notebook)
                        except (OSError, ValueError) as exc:
                            executed, execution_note = None, "Evaluator setup failed: " + redact(str(exc))
                    blocked = execution_note if not executed or (execution_note or "").startswith("Environment:") else None
                    criteria = assess(snapshot.notebook, executed, blocked)
                except NotebookMissing as exc:
                    result = Result("warning", result.primary, result.state, str(exc))
                except LookupFailure as exc:
                    result = Result("unverifiable", result.primary, result.state, str(exc))
            updated_items.append((student, assignment, result))
            assessments.append((student, result, snapshot, criteria, execution_note))
        items = updated_items
    try:
        path = write_report(items, output_dir)
        if assignments == (1,):
            for index, (student, result, snapshot, criteria, execution_note) in enumerate(assessments, 1):
                write_assignment_report(path.with_name(f"{path.stem}-student-{index}.md"), student, result,
                                        snapshot, criteria, execution_note)
    except OSError as exc:
        print(f"Could not write reports: {exc}")
        return 2
    counts = {kind: sum(result.kind == kind for _, _, result in items) for kind in ("submitted", "not_submitted", "warning", "unverifiable")}
    print(f"Students: {len(items)} (submitted: {counts['submitted']}, not submitted: {counts['not_submitted']}, warnings: {counts['warning']}, errors: {counts['unverifiable']})")
    print(path)
    return 0 if not counts["warning"] and not counts["unverifiable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
