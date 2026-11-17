"""Container-only notebook runner. The host never imports or executes student cells."""

import shutil
import sys
from pathlib import Path

import nbformat
from course_workspace import substitute_assigned_pdfs
from nbclient import NotebookClient


def main() -> int:
    source = Path(sys.argv[1])
    submitted = nbformat.read(source, as_version=4)
    workspace = Path("/work/dsi_deploying_ai_2026")
    activities = workspace / "02_activities"
    activities.mkdir(parents=True)
    helpers = workspace / "05_src"
    helpers.mkdir()
    (helpers / "utils").symlink_to("/course/05_src/utils", target_is_directory=True)
    documents = Path("/course/02_activities/documents")
    for pdf in Path("/course/trusted_documents").glob("*.pdf"):
        shutil.copy2(pdf, documents / pdf.name)
    for source in Path("/input/files").rglob("*"):
        if not source.is_file() or source.suffix.lower() != ".txt":
            continue
        relative = source.relative_to("/input/files")
        if relative.parts[:2] == ("02_activities", "documents"):
            target = documents / relative.relative_to("02_activities/documents")
        else:
            target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (workspace / "pyproject.toml").symlink_to("/course/pyproject.toml")
    (activities / "documents").symlink_to("/course/02_activities/documents", target_is_directory=True)
    notebook, substitutions, unresolved = substitute_assigned_pdfs(submitted, activities)
    notebook.metadata["assignment_review"] = {"substitutions": substitutions, "unresolved": unresolved}
    client = NotebookClient(notebook, timeout=300, kernel_name="python3", allow_errors=True)
    client.execute(cwd=str(activities))
    sys.stdout.write(nbformat.writes(notebook))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
