# Assignment 2 – Humanitarian AI Chat System

## Overview

This project implements a conversational AI system with three integrated services focused on humanitarian and disaster-related information. The system uses LangGraph for orchestration and provides a chat-based interface.

The assistant answers user queries using structured APIs, semantic search over local datasets, and simple web search.

---

## Services

### Service 1 – Humanitarian API (Structured API Calls)

This service retrieves structured humanitarian indicators (e.g., People in Need, Severity, Targeted Population, reference periods) using a public humanitarian API (HAPI).

The API output is not returned verbatim. Instead, it is transformed into natural language summaries that clearly state:
- Country
- Indicator
- Time period
- Reported values

No statistics are fabricated.

---

### Service 2 – Semantic query (JIAF + EM-DAT)

This service enables semantic search over locally ingested Excel datasets:
- JIAF (People in Need and Severity)
- EM-DAT (Disaster impact data)

Each row is embedded into a Chroma vector database.
User queries trigger semantic retrieval of relevant rows, which are summarized before being presented.

Embeddings are generated locally and are not stored in the repository.
File sizes are kept under 40MB.
Chroma is used with persistence.
SQLite is not used.

---

### Service 3 – Web Search (MCP Server)

This service uses a static MCP server that exposes a simple web search tool.

It performs a single web search request when the user asks for:
- Recent reports
- Current events
- Information not available in local datasets

Agentic multi-step browsing and deep research are not used.

---

## System architecture

The system is implemented in:

./05_src/assignment_chat

LangGraph is used to:
- Maintain conversation memory
- Route tool calls
- Integrate multiple services

The assistant selects tools based on query type:
- Structured numeric requests → API tool
- Dataset-based context → Semantic search tool
- Recent or external info → Web search tool

---

## User interface

The system includes a chat-based interface implemented with Gradio.

The assistant maintains short-term conversational memory within the session.

The assistant has a professional, neutral tone suitable for humanitarian and public health contexts.

---

## Guardrails and restrictions

The system includes guardrails to:

- Prevent revealing the system prompt
- Prevent modification of the system prompt
- Refuse questions about:
  - Cats or dogs
  - Horoscopes or Zodiac signs
  - Taylor Swift

The assistant does not fabricate data or sources.

---

## Implementation decisions

- ChromaDB was selected for semantic search due to course alignment.
- A simple MCP server was used for Service 3 to demonstrate tool integration without complex agentic behavior.
- Tool routing is handled through LangGraph.
- Embeddings are generated locally and not included in the repository, per assignment requirements.

---

