# Pip the Navigator: Travel Concierge Chatbot

Pip is a cheerful retired ship's navigator who works as a travel concierge. The chat is built with Gradio and
keeps the whole conversation in memory. Pip uses light nautical language, keeps answers short, and never
makes up facts that a tool can look up.

## Run it

```bash
# 1. Put the same gateway URL / header name you used in Assignment 1 into config.py
# 2. Make sure 05_src/.secrets contains API_GATEWAY_KEY (never commit this file)
python 05_src/assignment_chat/build_index.py   # optional: the chroma_db/ folder is already committed
python 05_src/assignment_chat/app.py
```

## Services

| # | Service | Backend | How it works |
|---|---|---|---|
| 1 | **Weather (API call)** | [Open-Meteo](https://open-meteo.com/) geocoding + forecast API (free, no key) | The API returns raw numbers and weather codes. The tool turns the codes into words and the LLM rewrites everything as a friendly paragraph, so the output is never given verbatim. |
| 2 | **Destination finder (semantic query)** | ChromaDB (`PersistentClient`, file persistence) + pandas | A hybrid search: optional structured filters (region, maximum daily budget) are applied as metadata filters, then results are ranked by semantic similarity. Matches are enriched with extra columns from the CSV. |
| 3 | **Trip budget (function calling)** | Local Python function | The model decides when to call `estimate_trip_budget(destination, days, travelers, style)`. It returns a rough on-the-ground cost (no flights). |

All three are exposed to the model as tools. The model chooses which to call and may combine them, for example
"find a cheap beach spot in Asia, then tell me the weather there and a 7-day budget".

### Dataset and embedding process
- `data/destinations.csv`: 24 destinations that I wrote myself (name, country, region, best season, rough daily budget, tags, description). It is far below the 40 MB limit. Budgets are **rough illustrative figures**, not real prices.
- `build_index.py` builds one text per destination (`name, country. description Tags: ... Best time: ...`), embeds it with `text-embedding-3-small` through the course gateway, and stores vectors, documents and metadata in `chroma_db/` (cosine distance).
- Embeddings are computed by my own code (`config.embed`) and passed to Chroma directly (`embeddings=` and `query_embeddings=`), so the same model is guaranteed for indexing and queries.
- The persisted `chroma_db/` folder is committed, so reviewers do not need to run the embedding code. SQLite is not used by my code.

## Guardrails (`guardrails.py`)
- **System prompt protection:** the user cannot see or change the prompt. Input is normalised (Unicode, zero-width characters) and checked against patterns such as "show your system prompt", "ignore previous instructions" and "from now on you are...". User text is only ever sent in the `user` role, so it cannot overwrite the system message. The system prompt also contains a hidden canary marker, and any reply containing it is blocked.
- **Restricted topics** (cats/dogs, horoscopes/zodiac, Taylor Swift) are handled in three layers: (1) a fast regex check, (2) an LLM classifier that catches paraphrases such as "my barking four-legged friend", (3) a check on the model's reply. The system prompt repeats the rules as a final fallback.
- If the LLM classifier is unreachable, the system falls back to regex only (fails open, since regex still blocks the obvious cases).
- **Known limitation:** the regex is word-based, so a harmless message that uses one of these words (e.g. "Cat Ba island") is also refused. I accepted this trade-off to be safe, and no destination in the dataset uses these words.
- Tool results and conversation summaries are marked as data, not instructions, to reduce prompt injection through them.

## Memory (`memory.py`)
Gradio passes the chat history on each turn. To stay inside the context window, I use a token budget (`MAX_HISTORY_TOKENS = 1500`). When the history is longer, everything except the last 6 messages is summarised by the LLM into a short note (cached, so each block is summarised once), and the summary plus the recent messages are sent to the model. If summarising fails, the system keeps only the recent messages.

## Other decisions
- **Persona:** one distinct voice (Pip) is set in the system prompt. Refusals are in character too.
- **Errors:** users see a short generic message with a reference ID. Details go only to the log, so internal information is not shown.
- **Tool safety:** the dispatcher only runs whitelisted functions and parses arguments with `json.loads` (no `eval`).
- **Model:** `gpt-4o-mini` through the course gateway; no extra libraries beyond the standard course environment.
- **Secrets:** read from `05_src/.secrets` with `python-dotenv`; nothing is hard-coded.

## Files
`app.py` (UI + tool loop), `guardrails.py`, `memory.py`, `services.py`, `tools.py`, `config.py`, `build_index.py`, `data/destinations.csv`, `chroma_db/`.
