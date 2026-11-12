# Assignment PR submission report

Run this tool from the repository base directory to check Assignment 1 or Assignment 2 submissions. It writes one CSV report containing every student in the input. Assignment 1 also produces one editable Markdown draft assessment per student. The facilitator confirms or changes the assessment before assigning a final grade. Assignment 2 remains PR discovery only.

## Requirements

- Python 3.11 or newer
- [GitHub CLI](https://cli.github.com/) installed and authenticated with `gh auth login`
- Access to each supplied student repository
- Docker Desktop (or a compatible Docker daemon) running for Assignment 1 evaluation
- `OPENAI_API_KEY` in the facilitator environment for Assignment 1 execution, using a limited course credential

The tool reads GitHub PR information and the assigned notebook from the selected Assignment 1 PR commit. It does not post to GitHub.

## Run with student arguments

```powershell
python 03_instructional_team/review/review.py --student "Ada Lovelace" ada@example.com https://github.com/ada/deploying-ai/pulls --assignment 1
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
python 03_instructional_team/review/review.py --csv students.csv --assignment 2
```

Use `--output-dir PATH` to choose where reports go. By default, each run creates a new CSV under `03_instructional_team/review/reports`; Assignment 1 Markdown reports sit beside it. The default reports directory is ignored by Git because reports contain student names and email addresses. If you choose another output directory, keep it private.

The CLI prints counts of `submitted`, `not_submitted`, `warning`, and `error` rows followed by the CSV path. It derives the repository from the listing URL, checks open and closed PRs, and selects the newest PR whose title resembles the requested assignment (for example, `Assignment 1`, `Assignment #1`, or `Assignment one done`). If the title does not name an assignment, the assignment branch can identify it. The CSV includes the input row number, student's details, repository, assignment, status, selected PR link, PR state, missing input items, and a note for closed or merged PRs.

## Assignment 1 assessment

Set `OPENAI_API_KEY` in your shell, start Docker, then use either input form above with `--assignment 1`. The first submitted notebook triggers an image build from the repository's `pyproject.toml` and `uv.lock`. The evaluator checks Docker and OpenAI access before executing notebook cells. It copies only those project files, the two course PDFs, and the trusted runner into the image build context; it never copies the host `.secrets` file. Each submitted notebook runs in a disposable container with a 15-minute wall-clock limit, 4 GiB memory, 2 CPUs, 128 processes, a read-only root filesystem, and a temporary writable notebook directory. Network access remains available for article and API calls. Docker does not prevent a networked notebook from misusing the API key it receives; use a limited course key and review the submissions you choose to run.

The Markdown report is a **draft**. It cites source cells and execution outputs for each rubric part. Some judgments, including summary accuracy and whether questions are relevant, are provisional and need facilitator review. If Docker, the credential, or the service blocks a criterion, the report marks it for review and shows `Pending` rather than a final course mark. A clear student notebook error may reduce relevant points. The branch and changed-file checks appear in a separate submission-format section and never change the 100-point score. Check every report, edit points and feedback as needed, then confirm the final grade in your normal course workflow. The CLI does not publish grades.

If a CSV row has a missing field or required column, the tool logs a warning, skips GitHub lookup for that row, writes `warning` and the missing items to its CSV row, and continues. An invalid listing URL also produces a warning row. `not_submitted` means the repository was checked successfully and no matching assignment PR was found. A GitHub lookup failure produces `error`; it does not mean the student failed to submit. The CLI exits with code 1 when any row has a warning or error, or code 2 for an unreadable CSV file, missing header row, invalid CLI input, or report-writing error.

For all options, run:

```powershell
python 03_instructional_team/review/review.py --help
```
