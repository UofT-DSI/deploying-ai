"""Bounded, redacted notebook evidence for an independent rubric review."""

import re
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

MAX_EVIDENCE_CHARS = 180_000
MAX_SOURCE_CHARS = 8_000
MAX_OUTPUT_CHARS = 3_000
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
GITHUB_URL = re.compile(r"https?://(?:www\.)?github\.com/[^\s'\"<>]+", re.IGNORECASE)
LOCAL_PATH = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|/(?:Users|home|content)/)[^'\"\r\n|]+", re.IGNORECASE)
KEY_PATTERN = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9_]{12,})\b")


@dataclass(frozen=True)
class EvidenceEntry:
    kind: str
    cell: int
    text: str


@dataclass(frozen=True)
class EvidenceBundle:
    entries: tuple[EvidenceEntry, ...]
    blocked: str | None = None
    reference_note: str | None = None

    def find(self, kind: str, cell: int, excerpt: str) -> bool:
        return bool(excerpt.strip()) and any(
            item.kind == kind and item.cell == cell and excerpt in item.text for item in self.entries
        )


class EvidenceLimit(ValueError):
    """The submitted evidence cannot fit in a complete judge request."""


def _text(value: object) -> str:
    if isinstance(value, list):
        return "".join(str(item) for item in value)
    return str(value or "")


def _redact(value: str, secrets: tuple[str, ...], student_name: str) -> str:
    for secret in secrets:
        if secret:
            value = value.replace(secret, "[credential]")
    if student_name:
        names = {student_name}
        names.update(part for part in student_name.split() if len(part) >= 3)
        for name in sorted(names, key=len, reverse=True):
            value = re.sub(rf"\b{re.escape(name)}\b", "[student]", value, flags=re.IGNORECASE)
    value = EMAIL.sub("[email]", value)
    value = GITHUB_URL.sub("[repository URL]", value)
    value = LOCAL_PATH.sub("[local path]", value)
    return KEY_PATTERN.sub("[credential]", value)


def _clip(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    marker = f"\n[... {len(value) - limit:,} middle characters omitted from judge view ...]\n"
    if len(marker) >= limit:
        return f"[entry omitted: {len(value):,} characters]"[:limit]
    retained = limit - len(marker)
    return value[:retained // 2] + marker + value[-(retained - retained // 2):]


@lru_cache(maxsize=2)
def _assigned_pdf_text(filename: str) -> str:
    from pypdf import PdfReader

    path = Path(__file__).resolve().parents[2] / "02_activities" / "documents" / filename
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def build_evidence(notebook: dict, executed: dict | None, blocked: str | None,
                   *, secrets: tuple[str, ...] = (), student_name: str = "") -> EvidenceBundle:
    from assignment_1_rubric import baseline_markdown

    entries = []
    code_source = []
    template = baseline_markdown()
    for index, cell in enumerate(notebook.get("cells", []), 1):
        if cell.get("cell_type") not in ("code", "markdown"):
            continue
        full_source = _redact(_text(cell.get("source", "")), secrets, student_name)
        if cell["cell_type"] == "code":
            code_source.append(full_source.lower())
        if cell["cell_type"] == "markdown":
            if full_source in template:
                full_source = "[unchanged course template markdown omitted]"
            else:
                prefix = next((text for text in template if text and full_source.startswith(text)), "")
                if prefix:
                    full_source = "[course template prefix omitted]\n" + full_source[len(prefix):]
        source = _clip(full_source, MAX_SOURCE_CHARS)
        entries.append(EvidenceEntry(cell["cell_type"], index, source))
    reference_note = "No trusted assigned PDF reference identified in notebook source."
    metadata = (executed or {}).get("metadata") or {}
    details = metadata.get("assignment_review") if isinstance(metadata, dict) else None
    substitutions = details.get("substitutions", []) if isinstance(details, dict) else []
    selected = next((item.get("article") for item in substitutions
                     if isinstance(item, dict) and item.get("article") in ("managing_oneself.pdf", "ai_report_2025.pdf")), None)
    if not selected:
        text = "\n".join(code_source)
        match = re.search(r"\b(managing_oneself|ai_report_2025)(?:\s*\(\d+\))?\.pdf\b", text)
        selected = match.group(1) + ".pdf" if match else None
    if selected:
        try:
            entries.append(EvidenceEntry("reference", 0, _assigned_pdf_text(selected)))
            reference_note = f"Trusted course reference: {selected}."
        except (OSError, ValueError):
            reference_note = f"Trusted course reference {selected} could not be read."
    if executed:
        for index, cell in enumerate(executed.get("cells", []), 1):
            rendered = {"output": [], "error": []}
            for output in cell.get("outputs", []):
                kind = "error" if output.get("output_type") == "error" else "output"
                data = output.get("data") or {}
                raw = output.get("text") or data.get("text/markdown") or data.get("text/plain") or output.get("evalue") or ""
                value = _redact(_text(raw), secrets, student_name)
                if value:
                    rendered[kind].append(value)
            for kind, values in rendered.items():
                if values:
                    entries.append(EvidenceEntry(kind, index, _clip("\n".join(values), MAX_OUTPUT_CHARS)))
    if sum(len(item.text) for item in entries) > MAX_EVIDENCE_CHARS:
        reference_size = sum(len(item.text) for item in entries if item.kind == "reference")
        other_count = sum(item.kind != "reference" for item in entries)
        limit = max(100, (MAX_EVIDENCE_CHARS - reference_size) // max(1, other_count))
        entries = [item if item.kind == "reference" else replace(item, text=_clip(item.text, limit))
                   for item in entries]
    total = sum(len(item.text) for item in entries)
    if total > MAX_EVIDENCE_CHARS:
        raise EvidenceLimit(f"Notebook evidence exceeds {MAX_EVIDENCE_CHARS:,} characters "
                            f"({len(entries)} entries, {total:,} characters after clipping)")
    return EvidenceBundle(tuple(entries), _redact(blocked, secrets, student_name) if blocked else None,
                          reference_note)
