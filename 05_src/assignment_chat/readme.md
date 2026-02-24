# Assignment Chat: Bureaucrat Buddy

## Personality
Bureaucrat Buddy responds in a memo-like bureaucratic tone: formal, structured, and slightly comedic.

## Services
### 1) Weather API (Open-Meteo)
- Uses Open-Meteo geocoding + forecast endpoints.
- Transforms the API output into a short “status memo” (no verbatim JSON).

### 2) Semantic Query (ChromaDB persistent)
- Dataset: `data/handbook.jsonl` (small AI deployment mini-handbook).
- Uses OpenAI embeddings (`text-embedding-3-small`).
- Chroma persistence: `chroma_store/` created on first run.
- On first run, embeddings are generated and stored locally; subsequent runs reuse persisted vectors.

### 3) Project Planner (Function Calling)
- Uses function calling to generate a structured project plan (milestones, risks, next actions).
- The plan is rendered into a readable format for the user.

## Chat Interface + Memory
- Gradio chat UI (`gr.ChatInterface`).
- Maintains conversation memory via `MemoryManager`.
- When conversation exceeds a simple context budget, older messages are summarized and kept as a running summary.

## Guardrails
- Blocks attempts to reveal/modify system or developer prompts.
- Refuses restricted topics: cats/dogs, horoscopes/zodiac signs, Taylor Swift.

## How to run
From repo root:

```bash
python -m 05_src.assignment_chat.app