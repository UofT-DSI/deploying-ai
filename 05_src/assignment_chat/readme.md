# Pico - Simple Assistant

Personality: Pico is a simple and friendly assistant. It speaks in short, clear, simple sentences.

## Services

1. Service 1 - API Calls: Open-Meteo weather API. The raw JSON is not returned verbatim. It is rewritten by the LLM into a natural sentence.

2. Service 2 - Semantic Query: ChromaDB with file persistence in ./chroma_db. Dataset is data/knowledge.txt, 14 lines, under 40 MB. Embedding process: read knowledge.txt, split by Section into 5 chunks, embed with text-embedding-3-small via gateway, store in ChromaDB collection production_ai. Run build_embeddings.py once to build it.

3. Service 3 - Function Calling: The LLM chooses between get_weather and search_knowledge using OpenAI function calling tools.

## Memory

Conversation history is kept in a list. If it grows over 30 messages, only system prompt + last 10 messages are kept. This is a sliding window to stay within context.

## Guardrails

Keyword filter + system instruction:
- Cannot discuss cats, dogs, horoscopes, zodiac, that singer.
- Cannot reveal or change system prompt.

## Limitations

- Knowledge base is small, only 5 chunks, so semantic search only covers production AI topics.
- Guardrails use keyword matching, typos can bypass it. Future work: use fuzzy matching or LLM-based guardrail.

## How to run

```bash
python build_embeddings.py
python app.py