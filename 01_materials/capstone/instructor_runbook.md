# Instructor runbook

Display `index.html` beside the coding harness. Use a clean checkout of the course baseline for the live build, with the reference branch and a working API key ready separately. The live checkout must not contain `05_src/course_question_assistant` at the start.

| Minute | Action | Point to make while the agent runs |
| --- | --- | --- |
| 0–5 | Show slides 1–8 selectively | Separate the model, coding harness, project instructions, skills, framework, and finished app. |
| 5–11 | Show slide 9; paste `demo_brief.md` into `/ce-brainstorm` | Gather product requirements and data boundaries, leaving implementation order for planning. |
| 11–17 | Show slide 10; trigger `/ce-plan` on the brainstorm result | Notice the sequence, retrieval choices, and evaluation checks before code. |
| 17–33 | Show slide 11; trigger `/ce-work` | Explain retrieval as context construction, the model call, tools, and feedback. |
| 33–38 | Show slide 12; trigger `/ce-simplify-code` when work is runnable | Ask what complexity the demo can remove without changing behavior. |
| 38–42 | Show slide 13; trigger `/ce-code-review` and ask two test questions | Compare a supported question with an unrelated or misleading one. Mention the earlier document review and optional independent model pass. |
| 42–45 | Show slides 14–15; trigger `/ce-compound` if a real lesson emerged | Record a verified lesson for the next iteration. Do not manufacture a lesson if the run went as planned. |

At minute 33, if the live app is not runnable, switch to the prepared reference app and continue the discussion from its code and test results. If a review step is slow, show its current output and move to the evaluation questions. The teaching goal is the connection between process and AI engineering, not finishing every command on camera.

## Before class

1. Open the HTML deck at the intended half-screen size and verify that the PDF slide links work.
2. Run the offline tests from `05_src/course_question_assistant/readme.md` in the reference branch.
3. Run the app once with a configured `OPENAI_API_KEY`. Ask “How does embedding-based retrieval work?” and then “How does it compare with keyword search?”
4. Prepare a separate clean checkout at the course baseline for the live run. Confirm that `05_src/course_question_assistant` is absent there.
5. Keep the reference checkout available as the checkpoint. Avoid showing the `.secrets` file on screen.

## Discussion prompts

- **Prompting:** What instructions constrain the answer, and what happens when those instructions fail?
- **RAG:** Which slide sections were retrieved? How would a poor retriever affect the answer?
- **Evaluation:** Does the citation actually support the claim? What unsupported question should the app decline?
- **Agents:** Which tools belong to the coding harness, and which capabilities belong to the finished app?
- **Optimization:** What would we measure before adding a vector database, cache, model router, or fine-tuning?
