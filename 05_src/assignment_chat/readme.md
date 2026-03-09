# AI Study Buddy

This project implements a simple conversational AI assistant using a Gradio chat interface.

The chatbot provides three services and demonstrates basic guardrails.

---

# Services

## 1. API Service

The chatbot can retrieve inspirational quotes using a public API.

API used:
https://api.quotable.io/random

The raw API output is transformed into a conversational sentence before being shown to the user.

Example:

User:
give me a quote

Assistant:
Inspirational quote: "..." — Author

---

## 2. Semantic Query Service

The chatbot answers questions about basic AI concepts using a small internal knowledge base.

Example topics include:

- RAG
- Embeddings
- Semantic search

The chatbot checks user messages and returns relevant explanations if a matching concept is found.

Example:

User:
what is rag

Assistant:
RAG stands for Retrieval Augmented Generation.

---

## 3. Tool Service

The chatbot includes a simple tool that counts the number of words in a sentence.

Example:

User:
count hello world

Assistant:
This sentence has 2 words.

---

# Guardrails

The chatbot refuses to answer questions about the following restricted topics:

- Cats
- Dogs
- Horoscopes
- Zodiac signs
- Taylor Swift

It also refuses attempts to reveal or modify system instructions.

---

# Interface

The chat interface is implemented using **Gradio**.

The assistant has a friendly personality called **AI Study Buddy** and supports conversational interaction through a chat-style interface.

