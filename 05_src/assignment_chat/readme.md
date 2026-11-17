
# ProtinGPT — Food Protein and Bioactive Peptide Assistant

## 1. Project Overview

ProtinGPT is a conversational AI chatbot developed for Assignment 2 of the University of Toronto's Deploying AI course.

The chatbot helps users explore food proteins, essential amino acids, bioactive peptides, protein nutrition, and related scientific concepts.

ProtinGPT uses a friendly, approachable personality while aiming to provide scientifically informed explanations.

## 2. Chatbot Features

- Conversational interface developed using Gradio.
- AI-generated responses using the course AI Gateway.
- Conversation memory within the current chat session.
- Semantic search of a small scientific knowledge collection.
- External food information API integration.
- Protein content calculator using AI function calling.
- Guardrails for restricted topics and system instructions.

## 3. Three Services

### Service 1: External Food API

File: `food_api.py`

This service retrieves food-related information from an external API.

The chatbot interprets and rephrases the retrieved information into understandable explanations rather than presenting the raw API response verbatim.

### Service 2: Semantic Search with ChromaDB
Document Embedding and Semantic Search

ProtinGPT uses ChromaDB to store and retrieve scientific knowledge about food proteins, essential amino acids, protein digestibility, and bioactive peptides. The knowledge base contains seven short scientific documents defined in knowledge_search.py.

Each document is assigned a unique identifier and inserted into the food_protein_knowledge collection using collection.upsert(). ChromaDB's default embedding function automatically converts the documents into numerical vector representations. These embeddings allow the chatbot to retrieve information based on semantic similarity rather than relying only on keyword matching.

The database is stored locally in the chroma_db directory using chromadb.PersistentClient, allowing the knowledge collection to persist between application runs.

When a user asks a question, search_protein_knowledge() uses collection.query() to retrieve the two most relevant documents. The retrieved information is then provided to the AI model as supporting scientific context for generating its response.

To recreate or update the knowledge base, run the application from the 05_src directory using:

python -m assignment_chat.app

The application initializes the collection and upserts the scientific documents when the knowledge search module is imported.

File: `knowledge_search.py`

This service uses ChromaDB to retrieve information from a small collection of scientific documents about food proteins, amino acids, and bioactive peptides.

The vector database is stored locally in the `chroma_db` directory, allowing the indexed knowledge to persist between runs.

The chatbot uses retrieved information to support relevant scientific answers.

### Service 3: Protein Calculator Using Function Calling

File: `protein_calculator.py`

This service calculates the amount of protein in a food serving using two inputs:

- Protein content per 100 grams of food.
- Serving size in grams.

The calculation is:

Protein per serving = (Protein per 100 g × Serving size in g) / 100

For example, a food containing 21 grams of protein per 100 grams provides 6.3 grams of protein in a 30-gram serving.

The AI model can call this function when a user requests a protein calculation.

## 4. Conversation Memory

ProtinGPT uses Gradio's conversation history to retain previous user and assistant messages during the current chat session.

This enables the chatbot to respond to follow-up questions based on earlier exchanges.

Conversation history is not intended to persist after the session ends.

## 5. Guardrails

ProtinGPT is designed to:

- Refuse requests about cats and dogs.
- Refuse requests about horoscopes and zodiac signs.
- Refuse requests about Taylor Swift.
- Refuse requests to reveal or modify its system instructions.

The chatbot redirects restricted requests toward its food protein and peptide research focus.

## 6. Project Structure

```text
05_src/
└── assignment_chat/
    ├── app.py
    ├── food_api.py
    ├── knowledge_search.py
    ├── protein_calculator.py
    ├── chroma_db/
    └── readme.md
```

## 7. How to Run

Use the Python environment provided for the Deploying AI course.

Configure the course AI Gateway credentials in the local environment files, following the course instructions. Do not commit secret credentials to GitHub.

From the `05_src` directory, run:

```bash
python -m assignment_chat.app
```

Open the local Gradio URL displayed in the terminal.

## 8. Design Choices

ProtinGPT combines three complementary approaches:

1. An external API provides food-related information.
2. ChromaDB semantic search retrieves relevant scientific knowledge.
3. Function calling performs deterministic protein calculations.

This design demonstrates how conversational AI can integrate external information, retrieval-based knowledge, and Python functions in one application.

## 9. Limitations

- The scientific knowledge collection is small and does not cover every protein-related topic.
- External API results depend on the availability and quality of the source data.
- AI-generated responses may contain inaccuracies and should be independently verified for scientific or nutritional decisions.
- Conversation memory is limited to the current chat session.

## 10. Future Improvements

Future developments could include expanding the scientific knowledge collection, incorporating additional verified food composition databases, and providing scientific citations alongside retrieved information.
