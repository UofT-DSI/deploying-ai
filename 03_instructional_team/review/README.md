# Assignment PR submission report

Run this tool from the repository base directory to check Assignment 1 or Assignment 2 submissions. It writes one CSV report containing every student in the input. Assignment 1 also produces one editable Markdown draft assessment per student. The facilitator confirms or changes the assessment before assigning a final grade. Assignment 2 remains PR discovery only.

## Requirements

- Python 3.11 or newer
- [GitHub CLI](https://cli.github.com/) installed and authenticated with `gh auth login`
- Access to each supplied student repository
- Docker Desktop (or a compatible Docker daemon) running for Assignment 1 evaluation
- `OPENAI_API_KEY` in the facilitator environment for Assignment 1 execution, independent AI review, and composite assessment, using a limited course credential

The tool reads GitHub PR information and the assigned notebook from the selected Assignment 1 PR commit. It does not post to GitHub.

## Run with student arguments

```powershell
uv run python 03_instructional_team/review/review.py --student "Ada Lovelace" ada@example.com https://github.com/ada/deploying-ai/pulls --assignment 1
```

Repeat `--student NAME EMAIL PULLS_URL` for more students. Use `--assignment 1` or `--assignment 2`. Run the tool separately for each assignment.

## Run with CSV

Create a UTF-8 CSV file with these headers. The `repo_url` column contains the repository's **pull request listing page**, ending in `/pulls` (a `/pull` ending is also accepted). Links using `www.github.com` are accepted:

```csv
name,email,repo_url
Ada Lovelace,ada@example.com,https://github.com/ada/deploying-ai/pulls
Grace Hopper,grace@example.com,https://github.com/grace/deploying-ai/pulls
```

Then run:

```powershell
uv run python 03_instructional_team/review/review.py --csv students.csv --assignment 2
```

Use `--output-dir PATH` to choose where reports go. By default, each run creates a new CSV under `03_instructional_team/review/reports`; Assignment 1 Markdown reports sit beside it. The default reports directory is ignored by Git because reports contain student names and email addresses. If you choose another output directory, keep it private.

The CLI prints counts of `submitted`, `not_submitted`, `warning`, and `error` rows followed by the CSV path. It derives the repository from the listing URL, checks open and closed PRs, and selects the newest PR whose title resembles the requested assignment (for example, `Assignment 1`, `Assignment #1`, or `Assignment one done`). If the title does not name an assignment, the assignment branch can identify it. The CSV includes the input row number, student's details, repository, assignment, status, selected PR link, PR state, missing input items, and a note for closed or merged PRs.

## Assignment 1 assessment

Set `OPENAI_API_KEY` in your shell, start Docker, then use either input form above with `--assignment 1`. The first submitted notebook triggers an image build from the repository's `pyproject.toml` and `uv.lock`. The evaluator checks Docker and OpenAI access before executing notebook cells. It copies only those project files, the two course PDFs, and the trusted runner into the image build context; it never copies the host `.secrets` file. Each submitted notebook runs in a disposable container with a 15-minute wall-clock limit, 4 GiB memory, 2 CPUs, 128 processes, a read-only root filesystem, and bounded writable `/work` and `/tmp` filesystems. The notebook input is mounted read-only. Notebook output is capped before the grader reads it. Network access remains available for article and API calls.

The host keeps the real OpenAI key. A temporary local gateway accepts a short-lived token from the container, forwards only approved API endpoints and models, and bounds request sizes and counts. Keep using a limited course key and review the submissions you choose to run because a networked notebook can still make allowed API calls through the gateway.

The image includes the trusted `05_src/utils` helpers and the two assigned course PDFs. The notebook starts in a bounded copy of the course directory layout, so course-relative imports and document paths work without mounting the host checkout. The host `.secrets` file is not included; the API gateway supplies a temporary container token. An unavailable PDF path is replaced only when its filename clearly identifies one of the assigned PDFs. The draft names the course copy and code cell used, while hiding the student's full local path. Ambiguous PDF references remain Pending; unrelated local files are not repaired.

The Markdown report is a **draft** with one proposed score out of 100. Complete begins at 60 points, Incomplete at 25, and Missing is below 25. A criterion blocked by the evaluator remains Pending even when assessed parts have a proposed subtotal. For the developer-and-user prompt criterion, either a `developer` or a `system` instruction role paired with a `user` role counts; the facilitator checks prompt quality. A `pypdf.PdfReader` call counts as content loading, and dynamic document text in a multiline prompt counts as source context. A measured summarization metric that prints `Score` and `Reason`, or printed G-Eval score and reason dictionaries, count toward the structured result. Revised-summary evaluation credit requires an observed Score and Reason tied to a successful evaluation; the values may be displayed separately in a later cell, as in the course lab. Source code alone does not earn runtime credit. Malformed execution output is unavailable evidence rather than proof of missing student work. A clear student notebook error leaves unobserved runtime parts without credit while preserving earlier observed outputs. The branch and changed-file checks remain outside the 100-point score. Check the proposed points, evidence, and learner feedback before confirming the final grade in the normal course workflow. The CLI does not publish grades.

After the existing rubric pass, the host sends a bounded, redacted view of the same notebook source and trusted execution outputs to an independent AI judge. Submitted saved outputs are excluded. Long cell content is shortened with an explicit omission marker; outputs from one cell are combined. When the notebook identifies an assigned course PDF, the judge also receives its trusted text. The independent judge does not see the first pass's scores. A later composite pass sees both reviews and proposes points for each rubric subpoint with a reason, exact evidence citations, and an uncertainty flag. Both requests use `store=false` and have no tools. Set `ASSIGNMENT_JUDGE_MODEL` or `ASSIGNMENT_COMPOSITE_MODEL` to change their models; the default is `gpt-4.1`. Invalid or unavailable composite output leaves the available non-AI points as a provisional proposal with an explicit issue. Disagreement still produces a proposed number and asks for facilitator review. The report leads with the composite rubric, then learner-facing strengths and improvements. Its final appendix has one row per rubric subpoint and the Non-AI Review, AI Review, and Composite Review side by side. The facilitator alone confirms the final grade.

### Review module interface

| Function | Parameters | Returns |
| --- | --- | --- |
| `build_evidence(notebook, executed, blocked, *, secrets=(), student_name="")` | `notebook`: submitted notebook dict; `executed`: trusted run dict or `None`; `blocked`: evaluator block or `None`; `secrets`: known credential strings; `student_name`: name to remove | `EvidenceBundle`; raises `EvidenceLimit` when complete evidence exceeds the request bound. |
| `rubric_specs(criteria)` | `criteria`: tuple of existing `Criterion` rows | Stable `PartSpec` IDs, labels, and point caps; no first-pass marks. |
| `judge_review(bundle, specs, *, client=None, model=None)` | `bundle`: redacted evidence; `specs`: rubric parts; `client`: optional OpenAI client; `model`: optional override | `JudgeReview` with one `Judgment` per part or an `issue`. |
| `composite_review(criteria, independent, bundle, *, client=None, model=None, secrets=(), student_name="")` | `criteria`: non-AI rows; `independent`: independent judge result; `bundle`: redacted evidence; `client`: optional OpenAI client; `model`: optional override; `secrets`: credentials to remove; `student_name`: name to remove | `CompositeReview` with a proposed judgment per part, learner notes, or an `issue`. |
| `reconcile(criteria, review, bundle, composite=None)` | `criteria`: first-pass rows; `review`: independent judge result; `bundle`: evidence used for citation validation; `composite`: optional composite result | `Reconciliation` with proposed rows and per-part `Decision` records. |

`EvidenceBundle.entries` contains `EvidenceEntry(kind, cell, text)` items. `kind` is `code`, `markdown`, `output`, `error`, or trusted `reference`; `reference` uses cell 0. `JudgeReview.judgments` contains `Judgment(part_id, points, status, evidence, reason)` items, where `evidence` is a tuple of `Citation(kind, cell, excerpt)`. `CompositeReview.judgments` contains `CompositeJudgment(part_id, points, status, evidence, reason, review_needed)` items. Its learner notes contain `FeedbackNote(part_id, text, evidence)`. `Reconciliation.criteria` holds the draft rows and `decisions` holds all three scores, reasons, and review flags. The module classes are immutable data records.

This example runs the same independent flow on a synthetic notebook. Set a limited `OPENAI_API_KEY` first:

```python
import sys

sys.path.insert(0, "03_instructional_team/review")
from assignment_1_evidence import build_evidence
from assignment_1_composite import composite_review
from assignment_1_judge import judge_review, rubric_specs
from assignment_1_reconcile import reconcile
from assignment_1_rubric import assess

notebook = {"cells": [{"cell_type": "code", "source": ["print('example')"]}]}
executed = {"cells": [{"outputs": [{"output_type": "stream", "text": "example"}]}]}
first = assess(notebook, executed)
bundle = build_evidence(notebook, executed, None)
independent = judge_review(bundle, rubric_specs(first))
composite = composite_review(first, independent, bundle)
draft = reconcile(first, independent, bundle, composite)
print(draft.issue or [(item.part_id, item.composite_score) for item in draft.decisions])
```

If a CSV row has a missing field or required column, the tool logs a warning, skips GitHub lookup for that row, writes `warning` and the missing items to its CSV row, and continues. An invalid listing URL also produces a warning row. `not_submitted` means the repository was checked successfully and no matching assignment PR was found. A GitHub lookup failure produces `error`; it does not mean the student failed to submit. The CLI exits with code 1 when any row has a warning or error, or code 2 for an unreadable CSV file, missing header row, invalid CLI input, or report-writing error.

For all options, run:

```powershell
uv run python 03_instructional_team/review/review.py --help
```
