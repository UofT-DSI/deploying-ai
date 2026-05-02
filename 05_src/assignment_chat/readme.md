# CodeBot-7: Your Sci-Fi Chat Buddy (Assignment 2)

CodeBot-7 is a witty sci-fi nerd chatbot with a love for bad puns and binary jokes. This project is implemented as part of Assignment 2, fulfilling all the requirements for a 3-service, LangGraph-orchestrated chat agent with robust guardrails.

## Features

### 1. Service 1: Public API Calls (`tools_api.py`)
Fetches random jokes from the Official Joke API. The agent transforms the JSON output into a natural-sounding, sci-fi themed response (preventing raw verbatim output).

### 2. Service 2: Semantic Query (`tools_semantic.py`)
Performs semantic search over a local dataset of movie reviews (`data/sample_reviews.txt`) using an embedded ChromaDB persistent client. 

**Embedding Process**:
To embed the dataset, the following logic was run once:
```python
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import os

client = chromadb.PersistentClient(path="./05_src/assignment_chat/chroma_db")
collection = client.get_or_create_collection(
    name="sample_reviews",
    embedding_function=OpenAIEmbeddingFunction(api_key=os.getenv("OPENAI_API_KEY"), model_name="text-embedding-3-small")
)

with open("05_src/assignment_chat/data/sample_reviews.txt") as f:
    lines = [line.strip() for line in f if line.strip()]
collection.add(documents=lines, ids=[f"doc_{i}" for i in range(len(lines))])
```
The data is persisted in the `chroma_db` directory (which keeps the file size extremely small, <<40MB). No SQLite is required.

### 3. Service 3: Function Calling (`tools_function.py`)
A custom math calculator utilizing OpenAI Function Calling to perform basic arithmetic (addition, subtraction, multiplication).

### Guardrails and Personality
The prompt (`prompts.py`) ensures:
- **System Prompt Protection**: CodeBot-7 will reject attempts to view or alter its instructions.
- **Restricted Topics**: Complete refusal to discuss Cats/Dogs, Horoscopes/Zodiac, or Taylor Swift.
- **Sci-Fi Tone**: Responses are short, punchy, and include terms like "galactic" and "system error".
- **Memory Management**: The agent limits conversation context window by summarizing if messages exceed 10.

## Run Instructions

1. Ensure your `.secrets` file has your `OPENAI_API_KEY`. (Copy `.secrets.template` to `.secrets` and update).
2. Install required packages (from the course standard setup).
3. From the `deploying-ai` root directory, execute:

```bash
python 05_src/assignment_chat/app.py
```
This will launch a Gradio interface. Open the local link in your browser to interact with CodeBot-7!
