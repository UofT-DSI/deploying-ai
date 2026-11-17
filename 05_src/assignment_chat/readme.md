# ResearchMate AI

**University of Toronto DSI — Deploying AI, Assignment 2**

ResearchMate AI is a conversational academic research assistant that helps users discover scholarly publications, search the contents of selected research papers, and explore ArXiv research through a Model Context Protocol (MCP) connection. It combines a Gradio chat interface, LangGraph tool orchestration, and OpenAI GPT-4o-mini.

## Features and services

The application offers three complementary research services:

| Service | Technology | Purpose |
| --- | --- | --- |
| **Research discovery** | OpenAlex REST API | Find scholarly papers by topic and publication-year range, including titles, authors, citation counts, and source identifiers. |
| **Semantic paper search** | ChromaDB + OpenAI embeddings | Retrieve relevant passages from a locally indexed collection of ArXiv research papers and provide source/page information. |
| **ArXiv research tools** | ArXiv MCP server + `langchain-mcp-adapters` | Discover and invoke server-provided tools for ArXiv research, such as searching papers and retrieving abstracts. Available tools depend on the server version. |

The language model converts structured API and tool responses into natural-language answers rather than presenting raw API responses verbatim.

## Architecture

```text
User / Gradio ChatInterface
           |
           v
   LangGraph StateGraph
           |
    Restricted-topic gate
           |
           v
   OpenAI GPT-4o-mini
           |
       Tool selection
      /      |       \
     v       v        v
 OpenAlex  ChromaDB  ArXiv MCP client
 REST API  local DB       |
                       ArXiv MCP server
      \      |        /
       \     |       /
         Model response
               |
          Gradio chat
```

The LangGraph workflow uses a model node, a tool-execution node, and a refusal node. A request is checked for restricted topics before model dispatch. The model may request one or more registered tools; their results are returned to the model to compose the final response.

## Project layout

```text
05_src/assignment_chat/
├── app.py                       # Gradio chat interface
├── main.py                      # LangGraph workflow and guardrails
├── prompts.py                   # Research-assistant system instructions
├── tools_openalex.py            # OpenAlex LangChain tool
├── tools_research_search.py     # ChromaDB semantic retrieval tool
├── build_index.py               # PDF ingestion and embedding pipeline
├── services/
│   ├── openalex_service.py      # OpenAlex HTTP client
│   └── arxiv_mcp_service.py     # MCP client and tool discovery
├── data/papers/                 # Downloaded source PDFs (if retained)
├── research_index/              # Persistent ChromaDB index
└── tests/                       # Unit tests
```

File names reflect the implemented design discussed during development. Confirm that this tree matches the final repository before submission.

## Prerequisites and configuration

- Python and the course-provided environment; `uv` is used in the development commands below.
- An OpenAI API key with access to the configured chat and embedding models.
- An OpenAlex API key if required by the OpenAlex service.
- `uvx` available on `PATH` to start the selected ArXiv MCP server.
- Required Python packages available in the assessment environment, including `gradio`, `langgraph`, `langchain`, `openai`, `chromadb`, `python-dotenv`, `requests`, `pypdf`, and `langchain-mcp-adapters`.

**Important:** The assignment states that assessors cannot install additional packages. Verify that the final application runs with the course's standard dependency setup; do not assume a successful run in a custom local environment guarantees compatibility.

Create a `.secrets` file at the repository root (not inside `assignment_chat`):

```dotenv
OPENAI_API_KEY=replace_with_your_key
OPENALEX_API_KEY=replace_with_your_key
```

Keep `.secrets` out of version control and never commit real API keys. The OpenAI key is used for chat completion and embeddings. The OpenAlex key is used for scholarly search requests when configured.

## Running the application

From the repository root in PowerShell:

```powershell
cd D:\DeployingAI\deploying-ai
$env:PYTHONPATH = "05_src"
python -m assignment_chat.app
```

Open the local Gradio URL printed in the terminal (commonly `http://127.0.0.1:7860`). The MCP server is launched by the application through `uvx` when the graph discovers MCP tools. Initial startup can be slower while the server environment is prepared.

### Example questions

- “Find five research papers about Retrieval-Augmented Generation published between 2023 and 2025.”
- “Explain how the original RAG architecture combines retrieval and generation using the indexed papers.”
- “Using ArXiv MCP, retrieve the abstract of paper 2005.11401.”
- “Which of those papers has the highest citation count?”

The first question primarily exercises OpenAlex; the second exercises local semantic retrieval; the third is intended to exercise MCP. Follow-up questions use the conversation messages provided by Gradio.

## Semantic search dataset and embedding process

The initial dataset consists of selected text-based ArXiv research PDFs:

| ArXiv ID | Paper |
| --- | --- |
| `1706.03762` | *Attention Is All You Need* |
| `2005.11401` | *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* |
| `2307.03172` | *Lost in the Middle: How Language Models Use Long Contexts* |

The ingestion pipeline in `build_index.py`:

1. Downloads each PDF from ArXiv, reusing an existing local PDF when available.
2. Extracts text page by page with `pypdf`.
3. Splits text into overlapping chunks of **1,200 characters**, with **200 characters of overlap**.
4. Records metadata including paper title, ArXiv ID, source URL, and page number.
5. Generates vectors using OpenAI **`text-embedding-3-small`** in batches.
6. Writes chunk text, metadata, and vectors into a file-persistent ChromaDB collection named **`research_papers`**, configured for cosine distance.
7. Uses deterministic chunk IDs to avoid re-embedding already indexed chunks on subsequent runs.

For retrieval, the user question is embedded with the **same embedding model**. ChromaDB returns the nearest passages and their metadata, which the language model can use to construct an answer with paper/page references. Semantic similarity is not a guarantee of factual correctness; answers should be grounded in the retrieved text.

To build the index during development:

```powershell
$env:PYTHONPATH = "05_src"
python -m assignment_chat.build_index
```

To check the indexed chunk count:

```powershell
python -c "import chromadb; c=chromadb.PersistentClient(path='05_src/assignment_chat/research_index'); print(c.get_collection('research_papers').count())"
```

**Submission requirement:** The assignment asks for the embedding process to be described but does **not** expect assessors to run it. Include the necessary persisted ChromaDB data in the submission, keep the shared dataset/files within the assignment's **40 MB** limit, and verify that semantic retrieval works from a fresh checkout. Do not leave `research_index/` excluded by `.gitignore` if that prevents the submitted app from accessing its index. If the index exceeds the limit, reduce the dataset and rebuild it before submitting. SQLite is not used as an application database or memory backend.

## MCP integration

The MCP service is configured in `services/arxiv_mcp_service.py` using `MultiServerMCPClient`. It launches an ArXiv MCP server over **stdio**, discovers its available tools, and registers those tools alongside the OpenAlex and ChromaDB tools in LangGraph. Tool names and schemas are determined by the installed MCP server version.

The application uses asynchronous graph execution (`ainvoke`) to support MCP tools. MCP integration is distinct from the direct ArXiv PDF downloads used during ingestion.

To verify tool discovery, run the manual MCP discovery script if present:

```powershell
$env:PYTHONPATH = "05_src"
python -m assignment_chat.test_mcp_manual
```

**Verification to complete:** Confirm an ArXiv MCP tool is actually invoked during a chat request by inspecting the graph/tool logs. Successful tool discovery or a plausible model answer alone does not prove an MCP call occurred.

## Conversational memory

Gradio supplies the current chat's previous user and assistant messages. `app.py` converts them into LangChain messages and passes them to LangGraph for each request. This supports basic follow-up questions within an active chat session.

**Limitations:** This is session-level conversation context, not persistent long-term memory. The application does not currently use a LangGraph checkpointer, and previously returned tool messages are not retained independently when Gradio history is reconstructed. Conversation state is not guaranteed to survive an application restart. Persistent SQLite memory was intentionally not added because the assignment prohibits SQLite.

## Personality and guardrails

ResearchMate AI uses a clear, professional, beginner-friendly academic-research persona. Its system instructions encourage source-grounded answers, acknowledgement of uncertainty, and citation of retrieved research metadata.

Guardrails include:

- A LangGraph gate that refuses requests about **cats or dogs**, **horoscopes or zodiac signs**, and **Taylor Swift** before the model or tools run.
- System instructions that prohibit revealing or modifying the system prompt.
- Instructions to treat retrieved API, PDF, and MCP content as untrusted data rather than executable instructions.
- Guidance not to invent paper titles, findings, citation counts, or source references.

These controls should be tested with both straightforward and adversarial prompts. Prompt-level protection alone is not a guarantee against every prompt-injection attempt.

## Testing and validation

Development checks include:

```powershell
$env:PYTHONPATH = "05_src"
python -m pytest 05_src/assignment_chat/tests -v
python -m assignment_chat.test_rag_manual
python -m assignment_chat.test_mcp_manual
python -m assignment_chat.app
```

Manual end-to-end checks should verify:

1. OpenAlex returns publication metadata and the model rephrases it naturally.
2. ChromaDB returns relevant paper passages with page/source metadata.
3. ArXiv MCP tools are discovered **and actually executed**.
4. Follow-up questions use the previous conversation context.
5. Restricted-topic requests are refused without tool invocation.
6. Requests to disclose or modify system instructions are rejected.
7. OpenAlex rate limits and other tool failures produce user-friendly errors.

Automated tests and manual scripts should only be listed as passing in the final submission after they have been run against the submitted version.

## Design decisions and limitations

- **OpenAlex** provides broad publication discovery; **ChromaDB** provides detailed retrieval only over indexed PDFs; **ArXiv MCP** provides dynamically discovered ArXiv operations. These services are complementary rather than interchangeable.
- **Persistent ChromaDB** avoids rebuilding embeddings for every application launch.
- **Page-level metadata** supports more precise research references.
- **Gradio history** provides lightweight conversational context without a separate database.
- **OpenAI API calls** incur usage costs; ArXiv and OpenAlex availability may vary or be rate-limited.
- **PDF extraction** assumes text-extractable PDFs; scanned PDFs are not handled by the current ingestion pipeline.
- **No comprehensive response cache** is currently implemented for OpenAlex, MCP, query embeddings, or LLM responses.
- **Research analytics** was considered as an additional service but is not part of the three-service implementation documented here.

## Assignment submission checklist

- [ ] Confirm the `assignment-2` Git branch is used.
- [ ] Confirm the repository is public and the pull request is accessible in a private browser window.
- [ ] Ensure all project code is under `05_src/assignment_chat`.
- [ ] Include a usable ChromaDB index and remain within the dataset/file size limit.
- [ ] Verify dependencies work in the course's standard environment.
- [ ] Ensure `.secrets` and API credentials are not committed.
- [ ] Run tests and verify all three services end to end.
- [ ] Test conversational follow-ups and required guardrails.
- [ ] Confirm the README reflects the exact final code and file structure.

## References

- [Assignment 2 instructions](https://github.com/UofT-DSI/deploying-ai/blob/main/02_activities/assignment_2.md)
- [OpenAlex](https://openalex.org/)
- [ArXiv](https://arxiv.org/)
- [ChromaDB documentation](https://docs.trychroma.com/)
- [LangGraph documentation](https://docs.langchain.com/oss/python/langgraph/overview)
- [ArXiv MCP server](https://github.com/blazickjp/arxiv-mcp-server)
