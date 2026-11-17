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
import threading
import urllib.error
import urllib.request
import uuid
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from api_gateway import notebook_gateway
from assignment_1_composite import composite_review
from assignment_1_evidence import EvidenceLimit, _redact, build_evidence
from assignment_1_judge import judge_review, rubric_specs
from assignment_1_reconcile import Reconciliation, reconcile
from assignment_1_rubric import assess, grade_label
from assignment_2_review import ai_pass as assignment_2_ai_pass
from assignment_2_review import (
    default_probes,
    mechanical_pass,
    run_project,
    runtime_evidence,
    secret_key,
    service_probes,
    source_evidence,
)
from assignment_2_review import reconcile as assignment_2_reconcile
from assignment_2_review import report as assignment_2_report
from assignment_2_submission import (
    ProjectMissing,
    ProjectUnavailable,
    fetch_project_snapshot,
)
from course_workspace import ASSIGNED_PDFS

DEFAULT_REPORTS = Path("03_instructional_team/review/reports")
COURSE_ROOT = Path(__file__).resolve().parents[2]
COURSE_HELPERS = (Path("05_src/utils/clients.py"), Path("05_src/utils/logger.py"))
COURSE_PDFS = tuple(Path("02_activities/documents") / name for name in ASSIGNED_PDFS)


@lru_cache(maxsize=1)
def course_image_name() -> str:
    digest = hashlib.sha256()
    files = [COURSE_ROOT / "pyproject.toml", COURSE_ROOT / "uv.lock",
             Path(__file__).with_name("Dockerfile"), Path(__file__).with_name("execute_notebook.py"),
             Path(__file__).with_name("course_workspace.py"), Path(__file__).with_name("execute_chat.py")]
    files.extend(COURSE_ROOT / pdf for pdf in COURSE_PDFS)
    files.extend(COURSE_ROOT / helper for helper in COURSE_HELPERS)
    for source in files:
        digest.update(str(source.relative_to(COURSE_ROOT)).encode("utf-8"))
        digest.update(source.read_bytes())
    return "assignment-1-evaluator:" + digest.hexdigest()[:16]


ASSIGNMENT_BRANCH = {1: "assignment-1", 2: "assignment-2"}
REPORT_FIELDS = ("input_row", "student_name", "email", "repo_url", "repository_url", "assignment", "status", "pr_url", "pr_state", "missing_items", "note")
ASSIGNMENT_TITLE = re.compile(r"\bassignment[\s#:_-]*(?:0*([12])|(one|two))\b", re.IGNORECASE)
LOCAL_PATH = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|/(?:Users|home|content)/)[^'\"\r\n|]+", re.IGNORECASE)


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
        content = payload["content"]
        if not isinstance(content, str):
            raise TypeError("invalid content data")
        notebook = json.loads(base64.b64decode(re.sub(r"[\t\n\r\f ]", "", content), validate=True))
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
            shutil.copy2(Path(__file__).with_name("execute_chat.py"), review_dir / "execute_chat.py")
            shutil.copy2(Path(__file__).with_name("course_workspace.py"), review_dir / "course_workspace.py")
            documents = context / "02_activities" / "documents"
            documents.mkdir(parents=True)
            for relative in COURSE_PDFS:
                shutil.copy2(COURSE_ROOT / relative, documents / relative.name)
            helpers = context / "05_src" / "utils"
            helpers.mkdir(parents=True)
            for relative in COURSE_HELPERS:
                shutil.copy2(COURSE_ROOT / relative, helpers / relative.name)
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
        request = urllib.request.Request("https://api.openai.com/v1/models",
                                         headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]})
        with urllib.request.urlopen(request, timeout=15):
            pass
    except (OSError, urllib.error.HTTPError) as exc:
        return "OpenAI service preflight failed: " + redact(str(exc))
    return None


MAX_NOTEBOOK_RESULT = 16 * 1024 * 1024
MAX_DOCKER_ERROR = 64 * 1024


def remove_container(name: str) -> None:
    try:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass


def capture_docker(command: list[str], name: str, timeout: int = 900) -> tuple[bytes | None, bytes, str | None]:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = [bytearray(), bytearray()]
    exceeded = threading.Event()

    def drain(stream, target: bytearray, limit: int) -> None:
        while chunk := stream.read(65536):
            remaining = limit - len(target)
            target.extend(chunk[:remaining])
            if len(chunk) > remaining:
                exceeded.set()
                try:
                    process.kill()
                except OSError:
                    pass
                return

    threads = [threading.Thread(target=drain, args=(process.stdout, output[0], MAX_NOTEBOOK_RESULT)),
               threading.Thread(target=drain, args=(process.stderr, output[1], MAX_DOCKER_ERROR))]
    for thread in threads:
        thread.start()
    issue = None
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        issue = "Notebook execution timed out; facilitator review required"
        process.kill()
    except KeyboardInterrupt:
        process.kill()
        remove_container(name)
        raise
    finally:
        for thread in threads:
            thread.join(timeout=5)
        process.stdout.close()
        process.stderr.close()
    if exceeded.is_set():
        issue = "Notebook execution unavailable: output exceeded limit"
    if issue:
        remove_container(name)
    return (bytes(output[0]) if not issue else None), bytes(output[1]), issue


def run_notebook(notebook: dict) -> tuple[dict | None, str | None]:
    name = "assignment-review-" + uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix="assignment-review-") as tmp:
        folder = Path(tmp)
        (folder / "notebook.ipynb").write_text(json.dumps(notebook), encoding="utf-8")
        with notebook_gateway(os.environ.get("OPENAI_API_KEY")) as gateway:
            command = ["docker", "run", "--rm", "--name", name, "--read-only",
                       "--tmpfs", "/tmp:rw,nosuid,size=256m", "--tmpfs", "/work:rw,nosuid,size=512m",
                       "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "128",
                       "--memory", "4g", "--cpus", "2", "--add-host", "host.docker.internal:host-gateway",
                       "--env", "HOME=/work", "--env", "IPYTHONDIR=/work/ipython",
                       "--mount", f"type=bind,source={folder.resolve()},target=/input,readonly"]
            if gateway:
                port, token = gateway
                command.extend(("--env", f"OPENAI_API_KEY={token}", "--env", f"OPENAI_BASE_URL=http://host.docker.internal:{port}/v1"))
            command.extend((course_image_name(), "python", "/course/execute_notebook.py", "/input/notebook.ipynb"))
            try:
                raw, stderr, issue = capture_docker(command, name)
            except OSError as exc:
                return None, f"Docker execution failed: {redact(str(exc))}"
        if issue:
            return None, issue
        try:
            executed = json.loads(raw)
        except (ValueError, TypeError, UnicodeError):
            error_text = stderr.decode("utf-8", "replace").split("Cell source:", 1)[0]
            exceptions = re.findall(r"(?m)^[\w.]*?(?:Error|Exception):[^\r\n]*", error_text)
            detail = next((line for line in reversed(exceptions) if not line.startswith("CellExecutionError:")),
                          exceptions[-1] if exceptions else error_text.strip().splitlines()[-1] if error_text.strip() else "runner returned no result")
            return None, "Notebook execution unavailable: " + redact(detail[:300])
        if not valid_execution_artifact(executed):
            return None, "Notebook execution unavailable: invalid result shape"
        errors = [(i, item) for i, cell in enumerate(executed["cells"], 1)
                  for item in cell.get("outputs", []) if item.get("output_type") == "error"]
        if errors:
            outcomes = [classify_execution_error(i, item, executed) for i, item in errors]
            return executed, next((issue for issue in outcomes if issue.startswith("Environment:")), outcomes[0])
        return executed, None


def classify_execution_error(cell: int, error: dict, executed: dict) -> str:
    name = str(error.get("ename", ""))
    message = redact(str(error.get("evalue") or name or "unknown error"))
    metadata = executed.get("metadata") or {}
    review = metadata.get("assignment_review") if isinstance(metadata, dict) else None
    unresolved = review.get("unresolved", []) if isinstance(review, dict) else []
    if name == "FileNotFoundError":
        for record in unresolved if isinstance(unresolved, list) else []:
            if (isinstance(record, dict) and record.get("cell") == cell
                    and record.get("reason") == "ambiguous assigned PDF"
                    and isinstance(record.get("basename"), str) and record["basename"] in message):
                return f"Environment: code cell {cell} has an ambiguous assigned PDF reference"
        if any(article in message.lower() for article in ASSIGNED_PDFS):
            return f"Environment: code cell {cell} could not access an assigned course PDF"
        if "/course/05_src/" in message or "/dsi_deploying_ai_2026/05_src/" in message:
            return f"Environment: code cell {cell} could not access a trusted course file"
        return f"Student: code cell {cell} raised FileNotFoundError for an unrelated local file"
    prefix = "Student" if name in STUDENT_ERRORS else "Environment"
    return f"{prefix}: code cell {cell} raised {clean_error(message)}"


def clean_error(value: str) -> str:
    return LOCAL_PATH.sub("[local path]", value).replace("\r", " ").replace("\n", " ")[:300]


STUDENT_ERRORS = {
    "NameError", "SyntaxError", "IndentationError", "TypeError", "AttributeError",
    "IndexError", "KeyError", "ZeroDivisionError", "AssertionError", "UnboundLocalError",
    "BadRequestError",
}


def valid_execution_artifact(value: object) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get("cells"), list):
        return False
    for cell in value["cells"]:
        if not isinstance(cell, dict) or not isinstance(cell.get("outputs", []), list):
            return False
        for item in cell.get("outputs", []):
            if not isinstance(item, dict):
                return False
            data = item.get("data", {})
            if not isinstance(data, dict):
                return False
            for text in (item.get("text", ""), data.get("text/plain", ""), data.get("text/markdown", "")):
                if not isinstance(text, str) and not (
                    isinstance(text, list) and all(isinstance(part, str) for part in text)
                ):
                    return False
    return True


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
                        logging.getLogger(__name__).warning("CSV row %s: %s; skipping lookup", row_number, issue)
                        students.append(Student(name, email, url, "", missing=missing, row_number=row_number, issue=issue))
                        continue
                    try:
                        students.append(make_student(name, email, url)._replace(row_number=row_number))
                    except ValueError as exc:
                        logging.getLogger(__name__).warning("CSV row %s: %s; skipping lookup", row_number, exc)
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
                            execution_note: str | None, substitutions: list[dict] | None = None,
                            second_pass: Reconciliation | None = None) -> None:
    def clean(value: object) -> str:
        return LOCAL_PATH.sub("[local path]", redact(str(value or ""))).replace("|", "\\|").replace("\r", " ").replace("\n", " ")

    def clean_evidence(value: object) -> str:
        return clean(_redact(str(value or ""), (os.environ.get("OPENAI_API_KEY", ""),), student.name))

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
        lines.extend([f"## Overall: {label} (draft)", "", f"Proposed score: {points:g} / 100.",
                      f"Proposed classification: {grade_label(points, False)} (draft; based on assessed points).",
                      percentage,
                      "The proposed score sums the rubric points supported by the available notebook evidence.",
                      "Facilitator confirmation is required before this is a final grade.", "",
                      "## Rubric", "", "| Criterion | Earned / available | Evidence and feedback |", "| --- | ---: | --- |"])
        for item in criteria:
            details = "; ".join(f"{part.label}: {'Pending' if part.pending else f'{part.earned:g}'}/{part.available:g} — {clean_evidence(part.evidence)}" for part in item.parts)
            row_score = f"{item.earned:g} / {item.available:g}" + (" assessed; pending parts excluded" if item.pending else "")
            lines.append(f"| {item.name}{' (review)' if item.pending else ''} | {row_score} | {details} |")
        decisions = {item.part_id: item for item in second_pass.decisions} if second_pass else {}
        indexed = [(f"c{row_index:02}p{part_index:02}", row.name, part)
                   for row_index, row in enumerate(criteria, 1)
                   for part_index, part in enumerate(row.parts, 1)]
        by_part = {part_id: (name, part) for part_id, name, part in indexed}
        contexts = {
            "Source selection and loading": ("This gives your summary a traceable source.", "Load the assigned article and show which text you used."),
            "Generation implementation": ("This makes your model request easier to reproduce.", "Show the prompt, source text, and model call used to generate the summary."),
            "Structured generation": ("This makes your result easier to inspect and reuse.", "Define and populate the required response fields."),
            "Generated content": ("This lets a reader judge your summary against the article.", "Show the generated summary and check it against the source article."),
            "Summarization evaluation": ("This gives evidence about your summary's coverage and accuracy.", "Run the summarization metric with questions tied to the article and show the result."),
            "G-Eval quality checks": ("This checks qualities beyond basic coverage.", "Apply the requested quality checks and display their results."),
            "Structured evaluation result": ("This makes each evaluation result inspectable.", "Display each score with its reason."),
            "Enhancement and reflection": ("This shows how you tested an improvement to your summary.", "Use the prior feedback in your revision, evaluate the new summary, and explain what changed."),
        }
        lines.extend(["", "## Encouraging observations", "",
                      "These are parts of your Assignment 1 work that you did well and are worth highlighting."])
        notes = [note for note in second_pass.encouragements if note.part_id in by_part
                 and by_part[note.part_id][1].earned > 0] if second_pass else []
        if notes:
            lines.extend(f"- {clean_evidence(note.text)}" for note in notes[:6])
        else:
            passed = [(name, part) for _, name, part in indexed if part.earned > 0 and not part.pending]
            lines.extend(f"- You met the {clean(part.label.lower())} part of {clean(name)}. "
                         f"{clean_evidence(part.evidence)}. {contexts[name][0]}" for name, part in passed[:6])
            if not passed:
                lines.append("- Your notebook needs a closer look before I can highlight a supported strength.")
        lines.extend(["", "## Specific improvements", "",
                      "Some Assignment 1 requirements were not fully met. These observations explain what to improve and why."])
        notes = [note for note in second_pass.improvements if note.part_id in by_part
                 and not by_part[note.part_id][1].pending
                 and by_part[note.part_id][1].earned < by_part[note.part_id][1].available] if second_pass else []
        if notes:
            lines.extend(f"- {clean_evidence(note.text)}" for note in notes)
        else:
            missed = [(name, part) for _, name, part in indexed
                      if not part.pending and part.earned < part.available]
            lines.extend(f"- The {clean(part.label.lower())} part of {clean(name)} could be stronger. "
                         f"{clean_evidence(part.evidence)}. {contexts[name][1]}" for name, part in missed)
            if not missed:
                lines.append("- No scored requirement gaps were identified. Check the provisional judgments against the source article.")
        if substitutions:
            lines.extend(["", "## Assigned PDF substitutions", ""])
            for record in substitutions:
                if (isinstance(record, dict) and isinstance(record.get("cell"), int)
                        and record["cell"] > 0 and record.get("article") in ASSIGNED_PDFS):
                    lines.append(f"- Code cell {record['cell']}: {record['article']} (course copy).")
        if execution_note:
            lines.extend(["", "## Execution note", "", clean_evidence(execution_note)])
        lines.extend(["", "## Submission format (outside points)", "",
                      f"- Branch: {clean(snapshot.branch) if snapshot else 'Unavailable'}" + (" (expected assignment-1)" if snapshot and snapshot.branch != "assignment-1" else ""),
                      "- Changes only assigned notebook: " + ("Yes" if snapshot and snapshot.changed_paths == ("02_activities/assignment_1.ipynb",) else "No"),
                      "- Changed files: " + (", ".join(clean(path) for path in snapshot.changed_paths) if snapshot else "Unavailable"), ""])
        lines.extend(["", "## Appendix: rubric review by subpoint", "",
                      "| Rubric element | Non-AI Review | AI Review | Composite Review |",
                      "| --- | --- | --- | --- |"])
        for part_id, name, part in indexed:
            decision = decisions.get(part_id)
            original = (f"{'Pending' if part.pending else f'{decision.original:g}'}/{part.available:g}: {clean_evidence(decision.original_evidence)}"
                        if decision else f"{'Pending' if part.pending else f'{part.earned:g}'}/{part.available:g}: {clean_evidence(part.evidence)}")
            if decision and decision.ai_status == "scored":
                cited = "; ".join(f"{item.kind} cell {item.cell}: {clean_evidence(item.excerpt[:80])}"
                                  for item in decision.evidence)
                ai = f"{decision.proposed:g}/{part.available:g}: {clean_evidence(decision.reason)}" + (f" [{cited}]" if cited else "")
            else:
                reason = decision.reason if decision else second_pass.issue if second_pass else "AI review was not run"
                ai = f"Unavailable: {clean_evidence(reason)}"
            if decision and decision.composite_score is not None:
                cited = "; ".join(f"{item.kind} cell {item.cell}: {clean_evidence(item.excerpt[:80])}"
                                  for item in decision.composite_evidence)
                composite_cell = (f"{decision.composite_score:g}/{part.available:g}: {clean_evidence(decision.composite_reason)}"
                                  + (f" [{cited}]" if cited else "")
                                  + (" Facilitator review needed." if decision.review_needed else ""))
            else:
                composite_cell = ("Unassessed" if part.pending else f"{part.earned:g}/{part.available:g} provisional")
                if second_pass and second_pass.issue:
                    composite_cell += f": {clean(second_pass.issue)}"
            lines.append(f"| {clean(name)} / {clean(part.label)} | {original} | {ai} | {composite_cell} |")
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
            substitutions = []
            second_pass = None
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
                    try:
                        bundle = build_evidence(snapshot.notebook, executed, blocked,
                                                secrets=(os.environ.get("OPENAI_API_KEY", ""),),
                                                student_name=student.name)
                        independent = judge_review(bundle, rubric_specs(criteria))
                        composite = composite_review(criteria, independent, bundle,
                                                     secrets=(os.environ.get("OPENAI_API_KEY", ""),),
                                                     student_name=student.name)
                        second_pass = reconcile(criteria, independent, bundle, composite)
                        criteria = second_pass.criteria
                    except EvidenceLimit as exc:
                        second_pass = Reconciliation(criteria, (), str(exc))
                    metadata = (executed or {}).get("metadata") or {}
                    details = metadata.get("assignment_review") if isinstance(metadata, dict) else None
                    if isinstance(details, dict) and isinstance(details.get("substitutions"), list):
                        substitutions = details["substitutions"]
                except NotebookMissing as exc:
                    result = Result("warning", result.primary, result.state, str(exc))
                except LookupFailure as exc:
                    result = Result("unverifiable", result.primary, result.state, str(exc))
            updated_items.append((student, assignment, result))
            assessments.append((student, result, snapshot, criteria, execution_note, substitutions, second_pass))
        items = updated_items
    if assignments == (2,):
        key = secret_key()
        setup_checked = False
        setup_issue = None
        updated_items = []
        for student, assignment, result in items:
            snapshot = None
            runtime = None
            scores = None
            first = None
            second = None
            baseline = None
            issue = None
            if result.kind == "submitted":
                try:
                    snapshot = fetch_project_snapshot(student.repo, result.primary, github_api)
                    source = source_evidence(snapshot, key)
                    probes = default_probes() + service_probes(source, key)
                    if not setup_checked:
                        setup_issue = build_image()
                        setup_checked = True
                    if setup_issue:
                        runtime = {"state": "unavailable", "reason": setup_issue, "exchanges": []}
                    else:
                        try:
                            runtime = run_project(snapshot, probes, key, course_image_name(), capture_docker, remove_container)
                        except OSError as exc:
                            detail = str(exc).replace(key, "[REDACTED]") if key else str(exc)
                            runtime = {"state": "unavailable", "reason": "Project launch unavailable: " + detail,
                                       "exchanges": []}
                    evidence = source + runtime_evidence(runtime, key)
                    baseline = mechanical_pass(evidence, runtime)
                    first, first_issue = assignment_2_ai_pass(evidence, key)
                    second, second_issue = assignment_2_ai_pass(evidence, key, first=first, baseline=baseline) if first else (None, first_issue)
                    scores = assignment_2_reconcile(first, second, runtime, baseline)
                    issue = second_issue or first_issue
                except ProjectMissing as exc:
                    result = Result("warning", result.primary, result.state, str(exc))
                except (ProjectUnavailable, LookupFailure) as exc:
                    result = Result("unverifiable", result.primary, result.state, str(exc))
            updated_items.append((student, assignment, result))
            assessments.append((student, result, snapshot, runtime, scores, issue, first, second, baseline))
        items = updated_items
    try:
        path = write_report(items, output_dir)
        if assignments == (1,):
            for index, (student, result, snapshot, criteria, execution_note, substitutions, second_pass) in enumerate(assessments, 1):
                write_assignment_report(path.with_name(f"{path.stem}-student-{index}.md"), student, result,
                                        snapshot, criteria, execution_note, substitutions, second_pass)
        if assignments == (2,):
            for index, (student, result, snapshot, runtime, scores, issue, first, second, baseline) in enumerate(assessments, 1):
                content = assignment_2_report(snapshot, runtime, scores, issue or result.reason, student.name,
                                              (result.primary or {}).get("html_url", ""), key, first, second, baseline)
                path.with_name(f"{path.stem}-student-{index}.md").write_text(content, encoding="utf-8")
    except OSError as exc:
        print(f"Could not write reports: {exc}")
        return 2
    counts = {kind: sum(result.kind == kind for _, _, result in items) for kind in ("submitted", "not_submitted", "warning", "unverifiable")}
    print(f"Students: {len(items)} (submitted: {counts['submitted']}, not submitted: {counts['not_submitted']}, warnings: {counts['warning']}, errors: {counts['unverifiable']})")
    print(path)
    return 0 if not counts["warning"] and not counts["unverifiable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
