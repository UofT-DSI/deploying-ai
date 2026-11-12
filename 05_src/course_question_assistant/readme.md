# Course question assistant

A small Gradio chat that answers questions from the Deploying AI Markdown slides. It uses a local term-based retriever over slide sections, sends selected passages to an OpenAI model, and displays the cited slide headings. It declines questions with weak retrieval evidence and hides model answers that contain no valid citation.

The coding agent used to build this project is separate from this app. The app does not run Codex, Claude Code, or Compound Engineering.

## Run

From the repository root, create a `.secrets` file containing `OPENAI_API_KEY=...` or set that environment variable directly. The course environment already declares Gradio, LangChain, and python-dotenv.

```powershell
$env:PYTHONPATH = '05_src'
uv run python -m course_question_assistant.app
```

On macOS or Linux:

```bash
PYTHONPATH=05_src uv run python -m course_question_assistant.app
```

Open the local URL printed by Gradio. Try “How does embedding-based retrieval work?” and then “How does it compare with keyword search?”

## Check the offline behavior

```powershell
$env:PYTHONPATH = '05_src'
python -m unittest discover -s 05_src/course_question_assistant -p 'test_*.py'
```

The tests use the real course slides and a stubbed model response; they do not need an API key. The retriever is intentionally simple. It is useful for showing the RAG flow, but a citation marker only proves that the answer points to a supplied passage, not that every claim is factually correct. Inspect responses and extend the evaluation set before using this as a student support service.
