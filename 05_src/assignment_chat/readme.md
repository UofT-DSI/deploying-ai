# Assignment 2 - assignment_chat

## Chat Client Overview
This chat client is named **Nova**, a concise and practical study companion for the Deploying AI course.

- Personality: encouraging, actionable, and concise
- Interface: Gradio chat interface (`ChatInterface`)
- Memory: conversation history is preserved by Gradio and trimmed to recent turns before model calls

## Services Implemented
The app provides at least three services, each accessible via chat commands.

### Service 1: API Calls (`/weather <city>`)
- Back end: Weatherstack Current Weather API (with Open-Meteo fallback)
- Behavior: transforms raw JSON API data into a short natural-language summary
- Requirement satisfied: API output is not returned verbatim

### Service 2: Semantic Query (`/search <question>`)
- Back end: semantic/hybrid search over Pitchfork JSONL files in `05_src/documents`
  - `pitchfork_content.jsonl`
  - `pitchfork_artists.jsonl`
  - `pitchfork_genres.jsonl`
  - `pitchfork_labels.jsonl`
  - `pitchfork_reviews.jsonl`
  - `pitchfork_years.jsonl`
- Vector store: ChromaDB **PersistentClient** stored in `./chroma_store`
- Retrieval strategy:
  - semantic retrieval with embeddings when OpenAI access is available
  - lexical fallback over the same dataset records when OpenAI access is unavailable

#### Embedding Process
1. Load all Pitchfork JSONL files from `05_src/documents`
2. Build a Chroma collection with persistent storage
3. Apply `text-embedding-3-small` through Chroma's OpenAI embedding function
4. Upsert documents + metadata + ids
5. Query with `collection.query(query_texts=[...])` for semantic search

### Service 3: Tool-based Service (`/plan <request>`)
- Approach: OpenAI Function Calling
- Tools:
  - `create_study_plan(topic, days, minutes_per_day)`
  - `estimate_quiz_count(available_minutes, question_difficulty)`
- Behavior: model decides tool call; app executes function; model returns final conversational response

## Guardrails and Restrictions
Guardrails block:
- attempts to reveal the system prompt
- attempts to modify/override the system prompt

Restricted topics are blocked:
- cats or dogs
- horoscopes or zodiac signs
- Taylor Swift

## File Map
- `app.py`: chat routing + Gradio interface
- `config.py`: constants and environment-aware OpenAI/gateway settings
- `guardrails.py`: safety checks
- `semantic_service.py`: indexing and retrieval
- `services.py`: API service + semantic response + function-calling service

## Run
From `05_src`:

```powershell
cd .\05_src
python -m assignment_chat.app
```

Commands:
- `/weather <city>`
- `/search <course question>`
- `/plan <study request>`
- `/reindex`

Weather service setup:
- add `WEATHERSTACK_API_KEY=<your_key>` to `05_src/.secrets` to enable Weatherstack as primary provider
