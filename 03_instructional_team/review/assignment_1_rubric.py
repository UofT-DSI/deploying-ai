"""Draft Assignment 1 rubric evidence from submitted code and notebook outputs."""

import ast
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ASSIGNED_SOURCES = ("managing_oneself", "Managing Oneself", "ai_report_2025", "GenAI Divide", "What is Noise", "newyorker.com")
FIELDS = ("Author", "Title", "Relevance", "Summary", "Tone", "InputTokens", "OutputTokens")


@lru_cache(maxsize=1)
def baseline_markdown() -> tuple[str, ...]:
    path = Path(__file__).resolve().parents[2] / "02_activities" / "assignment_1.ipynb"
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    return tuple("".join(cell.get("source", [])) for cell in notebook.get("cells", [])
                 if cell.get("cell_type") == "markdown")


def metric_questions(code: list[tuple[int, str]]) -> dict[str, tuple[int, list[str]]]:
    found = {}
    variables = {}
    for cell_number, source in code:
        sanitized = "\n".join("" if line.lstrip().startswith(("%", "!")) else line for line in source.splitlines())
        try:
            tree = ast.parse(sanitized)
        except SyntaxError:
            continue
        def strings(node):
            if isinstance(node, ast.Name):
                return variables.get(node.id, [])
            if isinstance(node, (ast.List, ast.Tuple)):
                return [item.value for item in node.elts if isinstance(item, ast.Constant) and isinstance(item.value, str)]
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variables[target.id] = strings(node.value)
            if not isinstance(node, ast.Call):
                continue
            function = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
            if function not in ("SummarizationMetric", "GEval"):
                continue
            keywords = {item.arg: item.value for item in node.keywords}
            if function == "SummarizationMetric":
                name, key = "summarization", "assessment_questions"
            else:
                title = keywords.get("name")
                name = str(title.value).lower() if isinstance(title, ast.Constant) else ""
                key = "evaluation_steps"
            if key in keywords:
                found[name] = (cell_number, strings(keywords[key]))
    return found


@dataclass(frozen=True)
class Part:
    label: str
    available: float
    earned: float
    evidence: str
    pending: bool = False


@dataclass(frozen=True)
class Criterion:
    name: str
    parts: tuple[Part, ...]

    @property
    def available(self) -> float:
        return sum(part.available for part in self.parts)

    @property
    def earned(self) -> float:
        return sum(part.earned for part in self.parts)

    @property
    def pending(self) -> bool:
        return any(part.pending for part in self.parts)


def grade_label(points: float, pending: bool = False) -> str:
    if pending:
        return "Pending"
    if points >= 60:
        return "Complete"
    if points >= 25:
        return "Incomplete"
    return "Missing"


def assess(notebook: dict, executed: dict | None = None, blocked: str | None = None) -> tuple[Criterion, ...]:
    cells = notebook.get("cells", [])
    code = [(i + 1, "".join(cell.get("source", []))) for i, cell in enumerate(cells) if cell.get("cell_type") == "code"]
    enhancement_start = next((i for i, cell in enumerate(cells, 1)
                              if cell.get("cell_type") == "markdown" and re.search(r"^#+\s*Enhancement\b", "".join(cell.get("source", [])), re.IGNORECASE | re.MULTILINE)),
                             len(cells) + 1)
    enhancement_code = [(i, source) for i, source in code if i > enhancement_start]
    original_markdown = baseline_markdown()
    added_markdown = []
    for i, cell in enumerate(cells, 1):
        if cell.get("cell_type") != "markdown":
            continue
        source = "".join(cell.get("source", []))
        if source in original_markdown:
            continue
        prefix = next((text for text in original_markdown if text and source.startswith(text)), "")
        added_markdown.append((i, source[len(prefix):]))
    combined = "\n".join(source for _, source in code)
    if not combined.strip():
        blocked = None
    outputs = []
    if executed:
        for i, cell in enumerate(executed.get("cells", []), 1):
            for item in cell.get("outputs", []):
                if item.get("output_type") == "error":
                    continue
                data = item.get("data") or {}
                raw = item.get("text") or data.get("text/markdown") or data.get("text/plain") or item.get("evalue") or ""
                outputs.append((i, "".join(raw) if isinstance(raw, list) else str(raw)))
    def field_value(text: str, name: str) -> str | None:
        quoted = re.search(rf"\b{re.escape(name)}['\"]?\s*[:=]\s*(['\"])(.*?)\1", text, re.IGNORECASE | re.DOTALL)
        if quoted:
            return quoted.group(2)
        line = re.search(rf"(?:^|\n|[{{,])\s*(?:\*\*)?['\"]?{re.escape(name)}['\"]?(?:\*\*)?\s*[:=]\s*([^\n,}}]+)", text, re.IGNORECASE)
        return line.group(1).strip() if line else None

    generated = next(((i, value) for i, value in outputs
                      if field_value(value, "Relevance") is not None
                      and field_value(value, "Summary") is not None), None)

    def generated_field(name: str) -> tuple[str, str] | None:
        if not generated:
            return None
        value = field_value(generated[1], name)
        return (f"Output cell {generated[0]} {name}: {value[:100]}", value) if value else None

    relevance = generated_field("Relevance")
    summary = generated_field("Summary")
    tone = generated_field("Tone")
    output_tokens = generated_field("OutputTokens")

    def summary_length() -> Part:
        if summary and output_tokens and output_tokens[1].isdigit() and int(output_tokens[1]) <= 1000:
            return Part("Summary at most 1,000 tokens", 2, 2, f"{output_tokens[0]} (whole response upper bound)")
        return Part("Summary at most 1,000 tokens", 2, 0,
                    "Summary-specific model token count unavailable; facilitator checks length", True)

    def match(pattern: str, flags: int = re.IGNORECASE) -> str | None:
        for i, source in code:
            found = re.search(pattern, source, flags)
            if found:
                line = source[source.rfind("\n", 0, found.start()) + 1:source.find("\n", found.end()) if "\n" in source[found.end():] else len(source)]
                return f"Code cell {i}: {line.strip()[:100]}"
        return None

    def output(pattern: str, after_cell: int = 0) -> str | None:
        for i, value in outputs:
            if i > after_cell and re.search(pattern, value, re.IGNORECASE):
                return f"Output cell {i}: {value.strip()[:100]}"
        return None

    def reflection(pattern: str) -> str | None:
        for i, source in enhancement_code:
            for line in source.splitlines():
                if line.lstrip().startswith("#") and re.search(pattern, line, re.IGNORECASE):
                    return f"Code cell {i} comment: {line.strip()[:100]}"
        for i, source in added_markdown:
            if i <= enhancement_start:
                continue
            found = re.search(pattern, source, re.IGNORECASE)
            if found:
                return f"Markdown cell {i}: {source.strip()[:100]}"
        return None

    def enhancement_match(pattern: str) -> str | None:
        for i, source in enhancement_code:
            found = re.search(pattern, source, re.IGNORECASE)
            if found:
                return f"Code cell {i}: {source.splitlines()[source[:found.start()].count(chr(10))].strip()[:100]}"
        return None

    def observed_enhancement_evaluation() -> str | None:
        evaluations = []
        for i, source in enhancement_code:
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            calls = [node.func for node in ast.walk(tree) if isinstance(node, ast.Call)]
            metrics = {call.value.id for call in calls if isinstance(call, ast.Attribute)
                       and call.attr == "measure" and isinstance(call.value, ast.Name)}
            direct_evaluate = any((isinstance(call, ast.Name) and call.id == "evaluate")
                                  or (isinstance(call, ast.Attribute) and call.attr == "evaluate") for call in calls)
            if metrics or direct_evaluate:
                evaluations.append((i, metrics))
        code_by_cell = dict(enhancement_code)
        output_by_cell = {}
        for i, value in outputs:
            output_by_cell.setdefault(i, []).append(value)
        for output_cell, values in output_by_cell.items():
            evaluation = next(((i, metrics) for i, metrics in reversed(evaluations) if i <= output_cell), None)
            if not evaluation or not executed:
                continue
            evaluation_cell, metrics = evaluation
            if any(item.get("output_type") == "error"
                   for cell in executed["cells"][evaluation_cell - 1:output_cell]
                   for item in cell.get("outputs", [])):
                continue
            value = "\n".join(values)
            if not field_value(value, "Score") or not field_value(value, "Reason"):
                continue
            source = code_by_cell.get(output_cell, "")
            if metrics and not any(
                re.search(rf"\b{re.escape(metric)}\s*\.\s*score\b", source)
                and re.search(rf"\b{re.escape(metric)}\s*\.\s*reason\b", source)
                for metric in metrics
            ):
                continue
            if output_cell != evaluation_cell and not metrics:
                continue
            return f"Output cell {output_cell}: revised summary Score and Reason; Code cell {evaluation_cell} evaluation"
        return None

    def observed_revised_summary() -> str | None:
        generations = [i for i, source in enhancement_code
                       if re.search(r"\bclient\.chat\.completions\.(?:parse|create)\s*\(", source)]
        for generated_cell in generations:
            for output_cell, value in outputs:
                if output_cell <= generated_cell or len(value.strip()) < 30:
                    continue
                source = dict(enhancement_code).get(output_cell, "")
                if not re.search(r"(?:print|display)\s*\([^)]*\.summary\b", source):
                    continue
                if executed and any(item.get("output_type") == "error"
                                    for cell in executed["cells"][generated_cell - 1:output_cell]
                                    for item in cell.get("outputs", [])):
                    continue
                return f"Output cell {output_cell}: revised summary after Code cell {generated_cell} generation"
        return None

    def applied_metric(name: str) -> str | None:
        metrics = set()
        applied = {}
        for i, source in code:
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                    func = node.value.func
                    constructor = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
                    keywords = {keyword.arg: keyword.value for keyword in node.value.keywords}
                    title = keywords.get("name")
                    matches = constructor == "SummarizationMetric" if name == "summarization" else (
                        constructor == "GEval" and isinstance(title, ast.Constant)
                        and str(title.value).lower() == name)
                    if matches:
                        metrics.update(target.id for target in node.targets if isinstance(target, ast.Name))
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "measure" and isinstance(node.func.value, ast.Name):
                        applied[node.func.value.id] = i
                    function = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
                    if function == "evaluate":
                        for keyword in node.keywords:
                            if keyword.arg == "metrics" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                                applied.update({item.id: i for item in keyword.value.elts if isinstance(item, ast.Name)})
        used = metrics & applied.keys()
        if used:
            metric = min(used)
            return f"Code cell {applied[metric]}: {metric} metric is applied"
        return None

    def measured_summarization_result() -> str | None:
        for i, source in code:
            if i >= enhancement_start or "SummarizationMetric" not in source:
                continue
            metric = re.search(r"\b(\w+)\s*=\s*SummarizationMetric\s*\(", source)
            if not metric:
                continue
            name = re.escape(metric.group(1))
            if not all(re.search(rf"\b{name}\s*\.\s*{attr}\b", source) for attr in ("measure", "score", "reason")):
                continue
            if executed and any(item.get("output_type") == "error" for item in executed["cells"][i - 1].get("outputs", [])):
                continue
            value = "\n".join(text for cell, text in outputs if cell == i)
            if field_value(value, "Score") and field_value(value, "Reason"):
                return f"Output cell {i}: Summarization Score and Reason"
        return None

    def structured_result(name: str) -> str | None:
        fields = {
            "Summarization": (("SummarizationScore", "SummarizationReason"),),
            "Coherence": (("CoherenceScore", "CoherenceReason"),),
            "Tone": (("ToneScore", "ToneReason"), ("TonalityScore", "Tonality")),
            "Safety": (("SafetyScore", "SafetyReason"), ("SafetyScore", "Safety")),
        }
        for i, value in outputs:
            if any(field_value(value, score) and field_value(value, reason) for score, reason in fields[name]):
                return f"Output cell {i}: {name} Score and Reason"
        return measured_summarization_result() if name == "Summarization" else None

    def part(label: str, points: float, evidence: str | None, runtime: bool = False) -> Part:
        if runtime and blocked and (not evidence or not evidence.startswith("Output cell")):
            return Part(label, points, 0, f"Evaluator blocked: {blocked}", True)
        return Part(label, points, points if evidence else 0, evidence or "No supporting evidence in submitted code or output")

    selected = next((match(re.escape(source)) for source in ASSIGNED_SOURCES if match(re.escape(source))), None)
    metric_steps = metric_questions(code)

    def question_score(name: str, maximum: float) -> tuple[float, str]:
        cell, questions = metric_steps.get(name, (0, []))
        bespoke = list(dict.fromkeys(question.strip() for question in questions
                                    if len(question.strip()) >= 12 and not re.search(r"what is (the )?(summary|text)|is this a good summary", question, re.IGNORECASE)))
        count = min(len(bespoke), 5)
        evidence = f"Code cell {cell}: {count} candidate questions/steps; facilitator checks relevance: " + "; ".join(bespoke[:5]) if count else "No bespoke metric questions/steps found"
        return count * maximum / 5, evidence

    summary_question_points, summary_question_evidence = question_score("summarization", 5)

    criteria = [
        Criterion("Source selection and loading", (
            part("Assigned article selected", 2, selected),
            part("Content loaded", 4, match(r"(PyPDFLoader|PdfReader|WebBaseLoader|open\(|load\(|requests\.get)")),
            part("Usable extracted text", 4, output(r".{40,}"), runtime=True),
        )),
        Criterion("Generation implementation", (
            part("OpenAI SDK", 3, match(r"\b(import openai|from openai import|OpenAI\()")),
            part("Non-GPT-5 model", 3, match(r"(model\s*=\s*['\"](?!gpt-5)[^'\"]+|['\"]gpt-4[^'\"]*['\"])")),
            part("Dynamic source context", 5, match(r"(f['\"].*\{.*(document|context|text)|\.format\(.*(document|context|text)|\bcontext\s*=)", re.IGNORECASE | re.DOTALL)),
            part("Developer and user prompts", 4, match(r"['\"](?:developer|system)['\"]") if match(r"['\"]user['\"]") else None),
        )),
        Criterion("Structured generation", (
            part("Pydantic BaseModel", 3, match(r"\bBaseModel\b")),
            *(part(f"Field {field}", 1, match(rf"\b{field}\b\s*[:=]")) for field in FIELDS),
            part("Input and output usage", 5, match(r"\.usage\b") if match(r"InputTokens") and match(r"OutputTokens") else None),
        )),
        Criterion("Generated content", (
            part("Professional relevance", 2, relevance[0] if relevance and re.search(r"professional|career|practitioner", relevance[1], re.IGNORECASE) else None, runtime=True),
            part("Relevance one paragraph", 2, relevance[0] if relevance and "\n\n" not in relevance[1] else None, runtime=True),
            part("Source-faithful summary", 2, summary[0] + " (facilitator verifies accuracy)" if summary else None, runtime=True),
            summary_length(),
            part("Distinguishable tone", 2, tone[0] if tone else None, runtime=True),
        )),
        Criterion("Summarization evaluation", (
            part("DeepEval summarization metric", 3, match(r"SummarizationMetric")),
            Part("Bespoke assessment questions", 5, summary_question_points, summary_question_evidence),
            part("Metric applied to summary", 2, applied_metric("summarization")),
        )),
        Criterion("G-Eval quality checks", tuple(
            item for topic, names in (("Coherence/clarity", ("coherence", "clarity")),
                                      ("Tonality", ("tonality", "tone")), ("Safety", ("safety",)))
            for name in (next((candidate for candidate in names if candidate in metric_steps), names[0]),)
            for score, evidence in (question_score(name, 3),)
            for item in (
                part(f"{topic} metric applied", 2, applied_metric(name) if name in metric_steps else None),
                Part(f"{topic} assessment questions", 3, score, evidence),
            )
        )),
        Criterion("Structured evaluation result", tuple(
            part(f"{name} Score and Reason", 2.5, structured_result(name), runtime=True)
            for name in ("Summarization", "Coherence", "Tone", "Safety")
        )),
        Criterion("Enhancement and reflection", (
            part("Context, summary, and evaluation in revision prompt", 3, enhancement_match(r"context") if enhancement_match(r"summary") and enhancement_match(r"evaluat") else None),
            part("Revised summary generated", 3, observed_revised_summary(), runtime=True),
            part("Revised summary evaluated", 3, observed_enhancement_evaluation(), runtime=True),
            part("Results compared", 3, reflection(r"compar|before|after|initial|first\s+prompt|final\s+prompt|higher|lower") if output(r".{10,}", enhancement_start) else None, runtime=True),
            part("Reflection on improvement and controls", 3, reflection(r"controls|adequate|limitations|improv")),
        )),
    ]
    return tuple(criteria)
