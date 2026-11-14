"""Container-only notebook runner. The host never imports or executes student cells."""

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def main() -> int:
    source = Path(sys.argv[1])
    notebook = nbformat.read(source, as_version=4)
    documents = Path("/work/documents")
    documents.symlink_to("/course/02_activities/documents", target_is_directory=True)
    client = NotebookClient(notebook, timeout=300, kernel_name="python3", allow_errors=True)
    client.execute(cwd="/work")
    sys.stdout.write(nbformat.writes(notebook))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
