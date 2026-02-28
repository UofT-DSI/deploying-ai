# SOC Mentor — Assignment 2

A conversational AI assistant designed for security analysts. Built with Gradio, OpenAI, and ChromaDB.

---

## Overview

**SOC Mentor** acts as a calm, experienced SOC (Security Operations Center) lead mentoring a junior analyst. It provides three distinct services via a Gradio chat interface.

---

## Services

### Service 1: UK Bank Holidays (API)
- **Backend:** [gov.uk Bank Holidays API](https://www.gov.uk/bank-holidays.json)
- **Feature:** User provides a region and date range; the assistant returns all bank holidays in that range.
- **Regions supported:** England & Wales, Scotland, Northern Ireland
- **Transformation:** Raw JSON from the API is passed to the LLM, which formats it into a natural language response.
- **Example query:** *"Show bank holidays in Scotland between 2026-01-01 and 2026-06-30"*

### Service 2: MITRE ATT&CK Semantic Search (ChromaDB)
- **Backend:** Persistent ChromaDB collection of ~100 MITRE ATT&CK Enterprise techniques
- **Feature:** User asks questions about attack techniques; the system performs semantic search and returns the most relevant techniques.
- **Embedding model:** `text-embedding-3-small` (OpenAI)
- **Response format:** Short summary + top matching technique IDs and names
- **Example query:** *"What techniques are used for credential dumping?"*

### Service 3: Microsoft Alert Triage (Function Calling)
- **Backend:** Custom Python tool using regex extraction + category-based templates
- **Feature:** User pastes a Microsoft Defender or Sentinel alert; the LLM calls the `ms_alert_triage` tool, which extracts IOCs and returns a structured triage checklist.
- **Alert categories supported:** Phishing, Malware, Credential Access, Persistence, Lateral Movement
- **Example query:** Paste a Defender alert and ask *"Can you triage this?"*

---

## Embedding Process

Embeddings were generated **once locally** and committed to the repo. The main app loads the persisted ChromaDB without re-generating embeddings.

**Steps used to generate embeddings:**
1. Downloaded the MITRE ATT&CK Enterprise STIX/JSON from [MITRE CTI GitHub](https://github.com/mitre/cti).
2. Ran `build_embeddings.py` to:
   - Parse ~100 techniques (only top-level T#### IDs, no sub-techniques)
   - Generate markdown files in `data/mitre_md/`
   - Embed each file using `text-embedding-3-small`
   - Persist the ChromaDB collection to `chroma_db/`
3. The `chroma_db/` folder was committed to the repository.

> **Graders:** You do not need to run `build_embeddings.py`. The persisted Chroma data is included.

---

## Guardrails

Implemented at the router level (before the LLM is called):

- **Blocked topics:** Cats, dogs, horoscopes/zodiac signs, Taylor Swift
- **System prompt protection:** Detects and blocks attempts to reveal or modify internal instructions

---

## Project Structure

```
05_src/assignment_chat/
├── app.py                        # Gradio entrypoint
├── config.py                     # Paths, constants, personality
├── router.py                     # Intent detection and routing
├── readme.md                     # This file
├── build_embeddings.py           # (Run once locally) Generates ChromaDB
├── services/
│   ├── bank_holidays_service.py  # Service 1
│   ├── mitre_search_service.py   # Service 2
│   └── soc_triage_tool.py        # Service 3 (function calling)
├── guardrails/
│   └── policy.py                 # Blocked topics + prompt protection
├── data/
│   ├── raw/                      # STIX/JSON source (optional)
│   └── mitre_md/                 # Generated technique markdown files
└── chroma_db/                    # Persisted ChromaDB (committed to repo)
```

---

## How to Run

```bash
export OPENAI_API_KEY=your_key_here
python app.py
```

Then open the Gradio link in your browser.

---

## Design Decisions

- **Routing is Python-based** (keyword matching in `router.py`) rather than tool-based, to keep services clearly separated and easy to grade.
- **LLM formats all responses** — services return structured data, and the LLM produces natural language output (satisfying the "transform/rephrase" requirement).
- **Guardrails are router-level** — blocked before the LLM sees the message, making them harder to bypass.
- **ChromaDB persistent client** used (not Docker) per assignment requirements. No SQLite code used directly.
