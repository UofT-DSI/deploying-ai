# Instructor runbook

Display `index.html` beside the coding harness. Start from this branch with a working API key ready. The live build creates `05_src/course_question_assistant` during class.

| Minute | Action | Point to make while the agent runs |
| --- | --- | --- |
| 0–5 | Show slides 1–8 selectively | Separate the model, coding harness, project instructions, skills, framework, and finished app. |
| 5–11 | Show slide 9; paste `demo_brief.md` into `/ce-brainstorm` | Gather product requirements and data boundaries, leaving implementation order for planning. |
| 11–17 | Show slide 10; trigger `/ce-plan` on the brainstorm result | Notice the sequence, retrieval choices, and evaluation checks before code. |
| 17–33 | Show slide 11; trigger `/ce-work` | Explain retrieval as context construction, the model call, tools, and feedback. |
| 33–38 | Show slide 12; trigger `/ce-simplify-code` when work is runnable | Ask what complexity the demo can remove without changing behavior. |
| 38–42 | Show slide 13; trigger `/ce-code-review` and ask two test questions | Compare a supported question with an unrelated or misleading one. Mention the earlier document review and optional independent model pass. |
| 42–45 | Show slides 14–15; trigger `/ce-compound` if a real lesson emerged | Record a verified lesson for the next iteration. Do not manufacture a lesson if the run went as planned. |

At minute 33, if the live app is not runnable, inspect the plan, code, and test results produced so far. Discuss the next check the agent should run and continue to the evaluation questions. If a review step is slow, show its current output. The teaching goal is the connection between process and AI engineering, not finishing every command on camera.

## Before class

1. Open the HTML deck at the intended half-screen size and verify that the PDF slide links work.
2. Confirm the Gradio and model dependencies in `pyproject.toml` are available and the API key is configured.
3. Confirm that `05_src/course_question_assistant` is absent before the live run.
4. Keep the build brief ready to paste into the harness. Avoid showing the `.secrets` file on screen.

## Discussion prompts

- **Prompting:** What instructions constrain the answer, and what happens when those instructions fail?
- **RAG:** Which slide sections were retrieved? How would a poor retriever affect the answer?
- **Evaluation:** Does the citation actually support the claim? What unsupported question should the app decline?
- **Agents:** Which tools belong to the coding harness, and which capabilities belong to the finished app?
- **Optimization:** What would we measure before adding a vector database, cache, model router, or fine-tuning?
