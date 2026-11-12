# Assignment PR review reports

Run this tool from the repository base directory to verify supplied Assignment 1 or Assignment 2 pull request links. It writes one local Markdown report per input record. These reports identify submissions; they do not grade them.

## Requirements

- Python 3.11 or newer
- [GitHub CLI](https://cli.github.com/) installed and authenticated with `gh auth login`
- Access to each supplied student repository

The tool only reads GitHub PR information. It does not clone repositories or post to GitHub.

## Run with student arguments

```powershell
python 03_instructional_team/review/review.py --student "Ada Lovelace" ada@example.com https://github.com/ada/deploying-ai/pull/42 --assignment 1
```

Repeat `--student NAME EMAIL PR_URL` for more students. Use `--assignment 1` or `--assignment 2`. Run the tool separately for each assignment.

## Run with CSV

Create a UTF-8 CSV file with these headers. The `repo_url` column contains the **pull request URL**, including `/pull/<number>`:

```csv
name,email,repo_url
Ada Lovelace,ada@example.com,https://github.com/ada/deploying-ai/pull/42
Grace Hopper,grace@example.com,https://github.com/grace/deploying-ai/pull/7
```

Then run:

```powershell
python 03_instructional_team/review/review.py --csv students.csv --assignment 2
```

Use `--output-dir PATH` to choose where reports go. By default, each run creates a new directory under `03_instructional_team/review/reports`. The default reports directory is ignored by Git because reports contain student names and email addresses. If you choose another output directory, keep it private.

The CLI prints a count of found submissions, warnings, and errors followed by every report path. Each report contains the student's details, supplied PR URL, repository, assignment, PR state when verified, and a grading-pending note. A closed or merged PR is identified in the report.

If a CSV row has a missing field or required column, the tool logs a warning, skips the GitHub lookup for that row, creates a report listing the missing items with **Status: Warning**, and continues to the next row. An invalid PR URL or a PR from the wrong assignment branch also produces a warning report. A GitHub lookup failure produces **Status: Error**; it does not mean the student failed to submit. The CLI exits with code 1 when any report has a warning or error, or code 2 for an unreadable CSV file, missing header row, invalid CLI input, or a report-writing error.

For all options, run:

```powershell
python 03_instructional_team/review/review.py --help
```
