"""Run a harmless notebook in the locked course image: python tests/smoke_docker.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import review


def main() -> int:
    issue = review.build_image()
    if issue:
        print(issue)
        return 1
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "cells": [
            {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
             "source": ["from pathlib import Path\n", "print('fixture', Path('documents/managing_oneself.pdf').exists())"]},
            {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
             "source": ["from IPython.display import Markdown, display\n",
                        "display(Markdown('**Score**: 0.8'))\n",
                        "display(Markdown('**Reason**: Improved clarity'))"]},
        ],
    }
    executed, issue = review.run_notebook(notebook)
    if issue:
        print(issue)
        return 1
    output = executed["cells"][0]["outputs"]
    text = "".join("".join(item.get("text", "")) if isinstance(item.get("text", ""), list)
                   else item.get("text", "") for item in output)
    if "fixture True" not in text:
        print("Notebook output did not confirm access to the course PDF:", text)
        return 1
    markdown = ["".join(item.get("data", {}).get("text/markdown", []))
                for item in executed["cells"][1]["outputs"]]
    if markdown != ["**Score**: 0.8", "**Reason**: Improved clarity"]:
        print("Notebook output did not preserve separate Markdown displays:", markdown)
        return 1
    print("Docker notebook smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
