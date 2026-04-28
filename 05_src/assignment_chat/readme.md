# Professor Aria — Academic Research Assistant

## Overview

Professor Aria is a conversational AI system built with Gradio and the OpenAI API.
She presents as a knowledgeable, intellectually warm academic research assistant
who helps users explore books, research literature, and current developments across
all academic disciplines.

---

## Services

### Service 1: Open Library API (Book Search)

**Trigger:** User asks about books, authors, reading recommendations, or bibliographies.

**How it works:**
- Queries the [Open Library Search API](https://openlibrary.org/dev/docs/api) — a free, no-key-required public API.
- Returns title, author(s), publication year, page count, and subject tags for the top 5 results.
- The assistant rephrases and enriches the results in Professor Aria's academic tone — never returning raw API output verbatim.

**Example queries:**
- "Find books by Yuval Noah Harari"
- "What books exist on cognitive science?"
- "Search for publications about machine learning"

---

### Service 2: Semantic Search over Research Abstracts (ChromaDB)

**Trigger:** User asks research questions, wants a literature overview, or queries a topic in depth.

**How it works:**
- A curated dataset of **50 research abstracts** spanning 10 academic fields was authored for this project:
  Climate Science, AI & Technology, Cognitive Psychology, Economics, Medicine,
  Education, Physics, History, Sociology, and Environmental Science.
- Abstracts are embedded using **`all-MiniLM-L6-v2`** (sentence-transformers) and stored in a
  **ChromaDB persistent client** at `./data/chroma_db/`.
- On first run, the collection is automatically seeded — no separate embedding script needs to be run.
- Cosine similarity is used for retrieval; top 3 results are returned with relevance scores.

**Embedding process:**
The `SentenceTransformerEmbeddingFunction` from `chromadb.utils.embedding_functions` handles
embedding generation inline during both ingestion and query. The model (`all-MiniLM-L6-v2`)
is downloaded automatically on first use via the `sentence-transformers` library.
No separate embedding pipeline script was needed given the small dataset size (50 documents).

**Example queries:**
- "What does research say about climate change and migration?"
- "Tell me about studies on cognitive behavioural therapy"
- "What is known about antibiotic resistance?"

---

### Service 3: Web Search via Function Calling (DuckDuckGo)

**Trigger:** User asks about recent, current, or latest developments in a topic.

**How it works:**
- Uses a two-step agentic pattern based on OpenAI **function calling** design:
  1. The model generates a refined, academic-focused web search query from the user's input.
  2. The refined query is sent to the **DuckDuckGo Instant Answer API** (free, no key required).
- Results (abstract, related topics, direct answers) are passed back to the assistant for natural synthesis.
- Chosen over the OpenAI `web_search` Responses API tool because the course gateway does not support the `/responses` endpoint.

**Example queries:**
- "What are the latest developments in quantum computing?"
- "Recent research on mRNA vaccines?"
- "Current news on large language models?"

---

## Guardrails

| Guardrail | Implementation |
|-----------|---------------|
| System prompt protection | Regex detection of injection phrases; canned refusal response |
| Prompt override prevention | Patterns like "ignore instructions", "you are now", "pretend to be" trigger refusal |
| Restricted topics | Regex on: cats, dogs, horoscopes, zodiac signs, Taylor Swift |
| Memory management | History trimmed to last 10 turns to stay within context window |

---

## Personality

Professor Aria is intellectually warm, precise, and encouraging. She uses academic
vocabulary naturally, contextualizes information with nuance, and always invites
further exploration. She never returns raw data — all service outputs are woven
into her conversational prose.

---

## Running the App

```bash
# From the repo root, activate your environment first
# Then:
cd 05_src/assignment_chat
python app.py
```

The Gradio interface will launch at `http://127.0.0.1:7860`.

---

## Dependencies

All dependencies are part of the standard course environment:
- `openai`
- `gradio`
- `chromadb`
- `sentence-transformers`
- `python-dotenv`
- `requests`

---

## Implementation Decisions

1. **Open Library over paid APIs:** Chosen because it is free, requires no API key,
   and aligns with the academic assistant theme.

2. **Custom abstract dataset:** Rather than using a pre-built dataset, 50 curated abstracts
   were written to ensure broad topical coverage and consistent quality for demonstration purposes.
   This also keeps the repository well under the 40 MB file size limit.

3. **DuckDuckGo for web search:** The course gateway blocks the OpenAI `/responses` endpoint,
   so the native `web_search` tool is unavailable. DuckDuckGo's Instant Answer API is free,
   requires no key, and supports the same agentic query-refinement pattern.

4. **Inline ChromaDB seeding:** Given the small dataset size, embeddings are generated and
   stored on first run rather than requiring a separate offline pipeline. This simplifies
   reproducibility for graders.

5. **Memory trimming:** Conversation history is capped at 10 turns (20 messages) to prevent
   context window overflow while maintaining conversational coherence.
