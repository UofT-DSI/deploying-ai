"""Small term-based retriever over the course's Markdown slides."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import math
import re


SLIDES_DIR = Path(__file__).resolve().parents[2] / "03_instructional_team" / "markdown_slides"
LESSONS = tuple(f"{number:02d}_{name}.md" for number, name in (
    (1, "introduction"),
    (2, "foundation_models"),
    (3, "evaluation"),
    (4, "prompt_engineering"),
    (5, "rag"),
    (6, "agents"),
    (7, "finetuning"),
    (8, "dataset_eng"),
    (9, "optimization"),
))
SKIP_HEADINGS = {"agenda", "references", "main points", "main points (cont.)"}
STOPWORDS = {
    "a", "an", "and", "are", "as", "based", "be", "can", "compare", "do",
    "does", "for", "from", "how", "i", "in", "is", "it", "my", "of", "on",
    "or", "the", "this", "to", "what", "when", "whole", "with", "work", "would",
}
ALIASES = {
    "evaluate": "evaluation", "evaluates": "evaluation", "evaluating": "evaluation",
    "evaluations": "evaluation", "systems": "system", "models": "model",
    "embeddings": "embedding", "agents": "agent",
}


@dataclass(frozen=True)
class Passage:
    file: str
    heading: str
    text: str


def _terms(text: str) -> set[str]:
    return {ALIASES.get(term, term) for term in re.findall(r"[a-z0-9]+", text.lower())
            if term not in STOPWORDS}


def _clean(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"<style>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "---" or stripped.startswith("!["):
            continue
        if stripped.startswith("# "):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"^[\s>*+-]+", "", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


@lru_cache(maxsize=1)
def load_passages() -> list[Passage]:
    passages = []
    for filename in LESSONS:
        raw = (SLIDES_DIR / filename).read_text(encoding="utf-8")
        raw = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", raw, count=1, flags=re.DOTALL)
        sections = re.split(r"(?m)^##\s+", raw)
        for section in sections[1:]:
            heading, _, body = section.partition("\n")
            heading = heading.strip()
            if heading.lower() in SKIP_HEADINGS:
                continue
            text = _clean(body)
            if len(_terms(text)) >= 5:
                passages.append(Passage(filename, heading, text[:1800]))
    return passages


def retrieve_passages(question: str, history: list[dict] | None = None, limit: int = 3) -> list[Passage]:
    """Return relevant slide passages, or none when term evidence is weak."""
    query = question
    if history and re.search(r"\b(it|that|they|those|this)\b", question.lower()):
        previous = next((item.get("content", "") for item in reversed(history)
                         if item.get("role") == "user" and isinstance(item.get("content"), str)), "")
        query = f"{previous} {question}"
    terms = _terms(query)
    if not terms:
        return []

    passages = load_passages()
    passage_terms = [_terms(f"{passage.heading} {passage.text}") for passage in passages]
    frequency = {term: sum(term in words for words in passage_terms) for term in terms}
    weights = {term: math.log((len(passages) + 1) / (count + 1)) + 1
               for term, count in frequency.items()}
    total_weight = sum(weights.values())
    ranked = []
    for passage, words in zip(passages, passage_terms):
        matches = terms & words
        if not matches:
            continue
        coverage_score = sum(weights[term] for term in matches)
        heading_score = sum(weights[term] for term in terms & _terms(passage.heading))
        score = coverage_score + 2 * heading_score
        ranked.append((score, coverage_score / total_weight, passage))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked or ranked[0][1] < 0.45 or (len(terms) > 1 and len(terms & _terms(f"{ranked[0][2].heading} {ranked[0][2].text}")) < 2):
        return []
    return [passage for score, coverage, passage in ranked[:limit] if coverage >= 0.2]
