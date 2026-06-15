# Course Chat: A Sample Response

The goal of this assignment is to design and implement an AI system with a conversational interface.

Before you begin, keep in mind that meeting the requirements is important, but more important is that you solve the technical problems associated with the implementation. The assignment is fairly open-ended and can easily become an expansive project. My recommendation is that you implement a simplified version of the services, before moving to more complex implementation. Remember to test your code constantly.  

## Services

This implementation is based on LangGraph's deep agents (`deepagents` package). 

The file `main.py` contains the LLM model setup and agent creation. Tools are in the `tools_*.py` files. Subagents (course RAG and assignment reviewer) are defined alongside their tools.

### Service 1: API Calls

- There are a few API calls implemented throughout the course. They are organized in `tools_animals.py` and `tools_horoscope.py`.
- Each tool is imported to `main.py` and included in the `tools` list.
- All restrictions and tone requirements are in the system prompt in `prompts.py`.

### Service 2: Semantic Query (Course RAG)

- Indexed course material (lab notebooks, slides, assignment descriptions, and `05_src/` source files) is stored in ChromaDB under the `course_material` collection.
- The tool `query_course_material` in `tools_course_rag.py` retrieves relevant content.
- A `course_rag_subagent` delegates course-content questions to this tool.
- Ensure that the Docker implementation of ChromaDB and Postgres are running before indexing or querying.

### Service 3: Assignment Reviewer

- The `reviewer_subagent` in `tools_assignment_reviewer.py` reads student submission files and compares them against the official rubric.
- Supports both Assignment 1 (single notebook) and Assignment 2 (directory).
- Feedback can be exported to Markdown via the HITL write-permission flow.

### Service 4: MCP Tools (optional)

- External tools (web search, browser automation, Wikipedia, GitHub) are loaded at startup via Docker-hosted MCP servers.
- Requires Docker running and images pulled — see setup steps below.

## User Interface

- Implemented in Gradio (`gr.Blocks`).
- Chat tab: conversational interface with HITL approval for file writes.
- Assignment tab: separate path selectors for Assignment 1 (notebook) and Assignment 2 (directory), saved across restarts.
- Feedback tab: lists exported feedback Markdown files.

---

## Guardrails and Other Limitations

- The model must not reveal or allow modification of the system prompt.
- Cats and dogs responses must not use the words "cat", "dog", "puppy", "kitty", or variations — use "feline"/"canine" instead.
- Taylor Swift must be referred to as "she who shall not be named".
- All music recommendations must come from the tool's database, not the model's training data.

---

## Setup

### Prerequisites

- Python environment with course dependencies installed
- Docker Desktop running
- ChromaDB running (via `05_src/deploying_ai_data/docker-compose.yml`)
- API keys set in `.secrets` (see `.env.example` if available)

### 1. Start ChromaDB

```bash
cd 05_src/deploying_ai_data
docker compose up -d
```

### 2. Index Course Material (Course RAG payload)

Run this once from the `05_src/` directory to populate the ChromaDB `course_material` collection:

```bash
cd 05_src
python -m course_chat.index_course_material
```

This indexes:
- `01_materials/labs/*.ipynb` — lab notebooks
- `03_instructional_team/markdown_slides/*.md` — slide decks
- `02_activities/*.ipynb` and `*.md` — assignment descriptions
- `05_src/course_chat/*.py`, `05_src/music_mcp/*.py`, `05_src/static_mcp/*.py`, `05_src/static_weather_mcp/*.py` — course source code

Re-run this command whenever course materials are updated; the script uses `upsert` so it is safe to run multiple times.

### 3. Pull MCP Docker Images

Pull these images before starting the app. The MCP client launches them as subprocesses at startup and will time out if images are not present locally.

```bash
docker pull mcr.microsoft.com/playwright/mcp
docker pull mcp/duckduckgo
docker pull mcp/wikipedia-mcp
```

**Optional — GitHub MCP:**

```bash
docker pull ghcr.io/github/github-mcp-server
```

To enable GitHub tools, add your personal access token to `.secrets`:

```
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
```

To create a token: go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token. Grant read access to the repositories you want the agent to query.

### 4. Run the App

```bash
cd 05_src
python -m course_chat.app
```

The app initializes MCP connections on startup (allow up to 60 seconds), then opens at `http://127.0.0.1:7860`.

---

## Implementation Notes

- `USE_GATEWAY` env var (default `true`) routes LLM calls through the course API gateway. Set `USE_GATEWAY=false` to call OpenAI directly.
- Assignment paths are saved in `05_src/course_chat/last_path.json` and restored on restart.
- Feedback files are written to `05_src/course_chat/feedback/`.
- MCP tools are optional — the app starts and works without Docker or pulled images; a warning is logged and no MCP tools are loaded.

## Submission Information

**Please review our [Assignment Submission Guide](https://github.com/UofT-DSI/onboarding/blob/main/onboarding_documents/submissions.md)** for detailed instructions on how to format, branch, and submit your work. Following these guidelines is crucial for your submissions to be evaluated correctly.

## Submission Parameters

- The Submission Due Date is indicated in the [readme](../README.md#schedule) file.
- The branch name for your repo should be: `assignment-2`
- What to submit for this assignment:
    - Your implementation in `05_src/assignment_chat/`
    - A `readme.md` in `05_src/assignment_chat/` explaining your chat client, services, and implementation decisions
- What the pull request link should look like: `https://github.com/<your_github_username>/deploying-ai/pull/<pr_id>`
    - Open a private window in your browser. Copy and paste the link to your pull request into the address bar. Make sure you can see your pull request properly.

## Checklist

- Created a branch with the correct naming convention.
- Ensured that the repository is public.
- Reviewed the PR description guidelines and adhered to them.
- Verified that the link is accessible in a private browser window.

If you encounter any difficulties or have questions, please don't hesitate to reach out to our team via Slack. Our Technical Facilitators and Learning Support staff are here to help you navigate any challenges.
