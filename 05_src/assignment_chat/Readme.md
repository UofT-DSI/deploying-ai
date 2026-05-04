
# Captain Jack Sparrow's Caribbean ChatBot

An AI-powered chatbot that speaks as Captain Jack Sparrow from Pirates of the Caribbean. 
The chatbot provides 2 services: sailing weather reports and shares tales of a Caribbean pirate (via semantic search).


## Services

### Service 1: Pirate Weather (API Call)

- Uses the [Open-Meteo API](https://open-meteo.com/) (free, no API key required) to fetch real-time weather conditions for Caribbean coordinates.
- Returns temperature and weather description in integer format. I have added a lookup dictionary to map the weather code to a more descriptive weather description.
- Jack Sparrow rephrases the raw weather data as a pirate captain's sailing assessment (e.g., "favorable winds for outrunning the Royal Navy").

- Implementation: `tools_get_sailing_weather.py`

### Service 2: Tales of Caribbean Pirates (Semantic Query via ChromaDB)

- A curated dataset of ~43 entries covering famous pirates (Blackbeard, Anne Bonny, Henry Morgan), legendary locations (Tortuga, Port Royal), ships (Queen Anne's Revenge, The Black Pearl), sea myths (Kraken, Davy Jones), and cursed treasures. This dataaset was generated using LLM and then manually reviewed and edited for accuracy and pirate authenticity.

- Stored in ChromaDB with file persistence logic (`PersistentClient`) — no Docker container needed.
- Embeddings are generated using OpenAI's `text-embedding-3-small` model via the course API gateway.
- Users ask questions like "Tell me about Blackbeard" or "What is Davy Jones' Locker?" and receive semantically matched stories/tales, narrated in Jack Sparrow's voice.

- Implementation: `tool_search_caribbean_tale.py`, `setup_tales_data.py`

#### Embedding Process

- The `setup_tales_data.py` script contains the tales dataset as Python strings and uses ChromaDB's `OpenAIEmbeddingFunction` to automatically embed each entry when added to the collection. This script needs to be **RUN ONCE** before starting the app. 
- The resulting `chroma_data/` directory is persisted to disk in the project directory.

## User Interface

- Built with gradio with basic design. 

- Note to Evaluator: I used AI to quickly enhace the UI design and make updates to simple chat interface code by gradio. 
- Sidebar includes a quick-start prompts to guide users to begin their interaction. 

- Jack Sparrow's personality is defined entirely through System prompt usage (no fine-tuning).

## Guardrails

- I uopdated these such that they sound more like Jack Sparrow himself rather than plain englist response.
Note to Evaluator: I used GoogleAI to get these responses;
--- How would Jack Sparrow respond to following: 

`how would jack sparrow from pirates of the carribians say the following; "I cannot respond to this topic about cats/dogs. Give small 1 liner suggestions for it."`
 output--- 
 "I’m afraid I must decline to weigh in on such a beastly matter, mate. 
 Cats/Dogs: "I don't fancy talk of four-legged beasts that don't pull an oar, mate."Horoscopes: "Me fate's written in the tides, not the twinklin' stars, savvy?"Taylor Swift: "I steer clear of sirens with catchy tunes and broken hearts."


## Architecture

```
app.py (Entry Point)
    |
Gradio ChatInterface
    |
    v
main.py (LangGraph Agent)
    |
    |-- SystemPrompt: Jack Sparrow personality (prompts.py)
    |-- Tool 1: get_sailing_weather (tools_weather.py) -> Open-Meteo API
    |-- Tool 2: search_caribbean_lore (tools_lore.py) -> ChromaDB PersistentClient
```

## Setup steps

Activate the course virtual environment:

```bash
source deploying-ai-env/bin/activate
```

2. Ensure `.secrets` file exists in `05_src/` with your `API_GATEWAY_KEY`.

### One-time data setup

Populate the ChromaDB collection with Caribbean tales embeddings:

```bash
python -m assignment_chat.setup_tales_data
```

 ```
 main ±  python -m assignment_chat.setup_tales_data
Setting up ChromaDB at /Users/sshukla/AIworkspace/DSI/deploying-ai/05_src/assignment_chat/chroma_data...
Deleting existing collection: caribbean_tales
Adding 43 tale entries to collection...
Collection 'caribbean_tales' created with 43 documents.
ChromaDB setup complete
```

### Run the app

`source deploying-ai-env/bin/activate`

`python -m assignment_chat.app`

```
2026-05-03 19:58:29,017, app.py, 39, INFO, Entering Jack Sparrow's Carribian world...
* Running on local URL:  http://127.0.0.1:7864
* To create a public link, set `share=True` in `launch()`.
```