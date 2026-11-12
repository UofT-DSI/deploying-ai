# Assignment PR review reports

Run this tool from the repository base directory to find students' Assignment 1 and Assignment 2 pull requests. It writes one local Markdown report per student and selected assignment. These reports identify submissions; they do not grade them.

## Requirements

- Python 3.11 or newer
- [GitHub CLI](https://cli.github.com/) installed and authenticated with `gh auth login`
- Access to each supplied student repository

The tool only reads GitHub PR information. It does not clone repositories or post to GitHub.

## Run with student arguments

```powershell
python 03_instructional_team/review/review.py --student "Ada Lovelace" ada@example.com https://github.com/ada/deploying-ai --assignment both
```

Repeat `--student NAME EMAIL REPO_URL` for more students. Use `--assignment 1`, `--assignment 2`, or `--assignment both`.

## Run with CSV

Create a UTF-8 CSV file with these headers:

```csv
name,email,repo_url
Ada Lovelace,ada@example.com,https://github.com/ada/deploying-ai
Grace Hopper,grace@example.com,https://github.com/grace/deploying-ai
```

Then run:

```powershell
python 03_instructional_team/review/review.py --csv students.csv --assignment 2
```

Use `--output-dir PATH` to choose where reports go. By default, each run creates a new directory under `03_instructional_team/review/reports`. The default reports directory is ignored by Git because reports contain student names and email addresses. If you choose another output directory, keep it private.

The CLI prints a count of found, absent, and unverifiable submissions followed by every report path. Each report contains the student's details, repository, assignment, PR link and status when found, and a grading-pending note. If several PRs use the assignment branch, the newest PR is primary and the others are listed. A closed or merged PR is identified in the report.

**Absent** means GitHub was checked successfully and no PR from the assignment branch was found. **Unverifiable** means the repository could not be checked; it does not mean the student failed to submit. The CLI exits with code 1 when any report is unverifiable, or code 2 for invalid intake, missing `gh`, or a report-writing error.

For all options, run:

```powershell
python 03_instructional_team/review/review.py --help
```
