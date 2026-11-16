"""Validate AI evidence before changing draft rubric points."""

import re
from dataclasses import dataclass, replace

from assignment_1_evidence import EvidenceBundle
from assignment_1_judge import Citation, JudgeReview, Judgment, rubric_specs
from assignment_1_rubric import Criterion

STRUCTURAL_POSITIVE = {
    "c01p02": r"\b(?:PdfReader|PyPDFLoader|WebBaseLoader|requests\.get)\b",
    "c02p03": r"(?:\{[^{}]*(?:document|context|text)[^{}]*\}|\.format\s*\()",
    "c02p04": r"['\"](?:system|developer)['\"](?s:.*)['\"]user['\"]|['\"]user['\"](?s:.*)['\"](?:system|developer)['\"]",
    "c07p01": r"\bScore\s*[:=].*\bReason\s*[:=]",
    "c07p02": r"\bCoherenceScore\s*[:=].*\bCoherenceReason\s*[:=]",
    "c07p03": r"\b(?:Tone|Tonality)Score\s*[:=].*\b(?:ToneReason|Tonality)\s*[:=]",
    "c07p04": r"\bSafetyScore\s*[:=].*\b(?:SafetyReason|Safety)\s*[:=]",
}
RUNTIME_PARTS = {"c07p01", "c07p02", "c07p03", "c07p04"}


@dataclass(frozen=True)
class Decision:
    part_id: str
    criterion: str
    label: str
    original: float
    proposed: float
    status: str
    reason: str
    evidence: tuple[Citation | tuple[str, int, str], ...]
    review_note: str = ""


@dataclass(frozen=True)
class Reconciliation:
    criteria: tuple[Criterion, ...]
    decisions: tuple[Decision, ...]
    issue: str | None = None
    model: str | None = None


def _citation(entry: Citation | tuple[str, int, str]) -> Citation:
    return entry if isinstance(entry, Citation) else Citation(*entry)


def _supports_change(judgment: Judgment, bundle: EvidenceBundle, available: float) -> bool:
    citations = tuple(_citation(entry) for entry in judgment.evidence)
    if not citations or not all(bundle.find(item.kind, item.cell, item.excerpt) for item in citations):
        return False
    if judgment.part_id in RUNTIME_PARTS and bundle.blocked:
        return False
    if judgment.points == available and judgment.part_id in STRUCTURAL_POSITIVE:
        required_kind = "output" if judgment.part_id in RUNTIME_PARTS else "code"
        cited_text = "\n".join(item.excerpt for item in citations if item.kind == required_kind)
        return bool(re.search(STRUCTURAL_POSITIVE[judgment.part_id], cited_text, re.IGNORECASE | re.DOTALL))
    if judgment.part_id == "c02p02" and judgment.points == 0:
        cited_text = "\n".join(item.excerpt for item in citations if item.kind == "code")
        if not re.search(r"\bmodel\s*=\s*['\"]gpt-5[^'\"]*['\"]", cited_text, re.IGNORECASE):
            return False
        all_code = "\n".join(item.text for item in bundle.entries if item.kind == "code")
        models = re.findall(r"\bmodel\s*=\s*['\"]([^'\"]+)['\"]", all_code, re.IGNORECASE)
        return bool(models) and all(model.lower().startswith("gpt-5") for model in models)
    return False


def reconcile(criteria: tuple[Criterion, ...], review: JudgeReview,
              bundle: EvidenceBundle) -> Reconciliation:
    if review.issue:
        return Reconciliation(criteria, (), review.issue, review.model)
    specs = rubric_specs(criteria)
    by_id = {item.part_id: item for item in review.judgments}
    decisions = []
    updated = []
    for row_index, row in enumerate(criteria, 1):
        parts = []
        for part_index, part in enumerate(row.parts, 1):
            spec = specs[sum(len(item.parts) for item in criteria[:row_index - 1]) + part_index - 1]
            judgment = by_id.get(spec.part_id)
            if judgment is None:
                parts.append(part)
                continue
            citations = tuple(_citation(entry) for entry in judgment.evidence)
            valid_citations = all(bundle.find(item.kind, item.cell, item.excerpt) for item in citations)
            supported_citation = valid_citations and (bool(citations) or judgment.points == 0)
            if judgment.status == "unavailable":
                status = "unavailable"
                parts.append(part)
                review_note = "The AI pass could not assess this subpoint."
            elif part.pending:
                status = "unavailable"
                parts.append(part)
                review_note = "The existing rubric marks this evidence as blocked or incomplete."
            elif judgment.points == part.earned:
                status = "agreed" if supported_citation else "unverified"
                parts.append(part)
                review_note = "" if supported_citation else "The AI citation does not match the available evidence."
            elif _supports_change(judgment, bundle, part.available) and not part.pending:
                status = "applied"
                evidence = "; ".join(f"{item.kind.title()} cell {item.cell}: {item.excerpt[:80]}" for item in citations)
                parts.append(replace(part, earned=judgment.points,
                                     evidence=f"AI-supported correction: {evidence}"))
                review_note = "The cited excerpt matches the structural scoring rule."
            else:
                status = "disputed"
                parts.append(replace(part, pending=True))
                review_note = ("The AI citation does not match the available evidence." if not valid_citations
                               else "The difference needs facilitator judgment or more execution evidence.")
            decisions.append(Decision(spec.part_id, row.name, part.label, part.earned,
                                      judgment.points, status, judgment.reason, citations, review_note))
        updated.append(replace(row, parts=tuple(parts)))
    return Reconciliation(tuple(updated), tuple(decisions), model=review.model)
