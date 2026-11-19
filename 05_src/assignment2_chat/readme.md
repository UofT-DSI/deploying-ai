# Alva: AI Workforce Readiness Advisor

Alva is a Gradio chatbot that helps managers, HR professionals, and team leads explore AI adoption, workforce skills, and organizational readiness. It uses the OpenAI Responses API, function calling, and conversation history to support follow-up questions.

## Services

1. **Recent AI Workforce News — NewsAPI:** `get_ai_workforce_news(role, topic, challenge)` retrieves relevant articles, including titles, publication dates, descriptions, and URLs. Alva summarizes their relevance rather than reproducing API responses verbatim. News availability depends on the search and API plan.

2. **Knowledge-Base Search — ChromaDB:** `search_alva_knowledge(query)` retrieves relevant passages from 10 Markdown summaries based on Microsoft Learn, Google AI Essentials, OpenAI documentation, and Prosci. Topics include AI fundamentals, responsible AI, prompt engineering, productivity, ADKAR, change management, adoption, and leadership.

3. **AI Readiness Recommendations — Function Calling:** `generate_ai_readiness_recommendation(role, challenge)` produces a short action plan covering skills assessment, training, AI champions, low-risk pilots, and feedback. Recommendations provide general guidance rather than a validated workforce assessment.

## Knowledge-Base Implementation

`ingest_alva.py` reads documents from `documents/alva/`, splits them into passages, and generates embeddings using `text-embedding-3-small` through the DSI API gateway.

Documents, embeddings, IDs, and source metadata are stored in the persistent ChromaDB collection `alva_workforce_readiness` under `chroma/alva_knowledge/`. The stored database is included so embeddings do not need to be regenerated.

**Knowledge-base sources:**
- Microsoft Learn: `ai_fundamentals.md`, `generative_ai.md`, `responsible_ai.md`
- Microsoft Learn and OpenAI: `prompt_engineering.md`
- Google AI Essentials: `ai_productivity.md`, `workplace_ai.md`
- Prosci: `adkar.md`, `change_management.md`
- Prosci and Microsoft Learn: `ai_adoption.md`, `ai_leadership.md`

Original source URLs are included in the Markdown documents.

## Running Alva

From the `05_src` directory, using the DSI course environment:

```bash
python -m assignment2_chat.app
```

The application requires the DSI `API_GATEWAY_KEY` and a `NEWS_API_KEY` in the local `.secrets` file.

If the ChromaDB database needs to be regenerated:

```bash
python -m assignment2_chat.ingest_alva
```

## Guardrails and Limitations

Alva is instructed not to reveal or modify its system instructions and to follow the assignment's restricted-topic requirements. It identifies sources where available and treats retrieved content as evidence rather than instructions.

NewsAPI articles may be delayed or unavailable, and the curated knowledge base may not reflect the latest developments.