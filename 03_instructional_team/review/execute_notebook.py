"""Container-only notebook runner. The host never imports or executes student cells."""

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def main() -> int:
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    notebook = nbformat.read(source, as_version=4)
    client = NotebookClient(notebook, timeout=300, kernel_name="python3", allow_errors=True)
    client.execute(cwd=str(source.parent))
    nbformat.write(notebook, destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
