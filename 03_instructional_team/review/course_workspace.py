"""Resolve assigned article paths in a disposable notebook copy."""

import ast
import copy
import io
import re
import tokenize
from pathlib import Path, PurePosixPath, PureWindowsPath

ASSIGNED_PDFS = {
    "managing_oneself.pdf": ("managingoneself", "druckerhbr"),
    "ai_report_2025.pdf": ("aireport2025", "genaidivide", "stateofaiinbusiness2025"),
}
COURSE_DOCUMENTS = PurePosixPath("/course/02_activities/documents")


def assigned_article(path: str) -> tuple[str | None, bool]:
    if re.match(r"^[a-z][a-z0-9+.-]*://", path, re.IGNORECASE):
        return None, False
    normalized = path.replace("\\", "/")
    if not normalized.lower().endswith(".pdf"):
        return None, False
    stem = re.sub(r"[^a-z0-9]", "", PurePosixPath(normalized).stem.lower())
    matches = [name for name, aliases in ASSIGNED_PDFS.items() if any(alias in stem for alias in aliases)]
    return (matches[0], False) if len(matches) == 1 else (None, len(matches) > 1)


def path_is_available(path: str, cwd: Path) -> bool:
    if PureWindowsPath(path).is_absolute() and not PurePosixPath(path).is_absolute():
        return False
    candidate = Path(path)
    return (candidate if candidate.is_absolute() else cwd / candidate).is_file()


def substitute_assigned_pdfs(notebook: dict, cwd: Path) -> tuple[dict, list[dict], list[dict]]:
    derived = copy.deepcopy(notebook)
    substitutions = []
    unresolved = []
    for cell_number, cell in enumerate(derived.get("cells", []), 1):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        source = "".join(source) if isinstance(source, list) else source
        tokens = []
        try:
            for token in tokenize.generate_tokens(io.StringIO(source).readline):
                if token.type != tokenize.STRING:
                    tokens.append(token)
                    continue
                try:
                    path = ast.literal_eval(token.string)
                except (ValueError, SyntaxError):
                    tokens.append(token)
                    continue
                if not isinstance(path, str):
                    tokens.append(token)
                    continue
                article, ambiguous = assigned_article(path)
                if ambiguous:
                    record = {"cell": cell_number, "reason": "ambiguous assigned PDF",
                              "basename": PurePosixPath(path.replace("\\", "/")).name}
                    if record not in unresolved:
                        unresolved.append(record)
                if not article or path_is_available(path, cwd):
                    tokens.append(token)
                    continue
                replacement = str(COURSE_DOCUMENTS / article)
                tokens.append(token._replace(string=repr(replacement)))
                record = {"cell": cell_number, "article": article}
                if record not in substitutions:
                    substitutions.append(record)
        except (tokenize.TokenError, IndentationError):
            continue
        cell["source"] = tokenize.untokenize(tokens)
    return derived, substitutions, unresolved
