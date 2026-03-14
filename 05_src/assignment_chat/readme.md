# Assignment 2 – Professor Byte Chatbot

## Overview

Professor Byte is a simple conversational AI chatbot developed for Assignment 2.

The chatbot provides a local web-based chat interface where users can ask questions and receive responses from an AI assistant. The system includes three routed services, short-term conversation memory through chat history, and simple guardrails for restricted requests.

This project was built using **Python**, **Gradio**, **LangChain message objects**, and the **OpenAI API**.

---

## Chatbot Personality

The assistant is called **Professor Byte**.

Professor Byte is a friendly and slightly witty academic assistant who explains ideas clearly and briefly.

---

## Features

### 1. Chat Interface

The chatbot uses **Gradio ChatInterface** to provide a simple local web-based chat system.

Users can type messages and receive responses in real time through a browser interface.

---

### 2. API Service

The chatbot includes one service that uses a **public API**.

In this project, the API service calls the **SpaceX API** and returns a short natural-language summary of the latest launch.

Example prompt: `Use the API service to summarize the latest SpaceX launch.`

---

### 3. Semantic Search Service

The chatbot includes a simple semantic-style search service using a small local knowledge base.

The knowledge base contains short explanations for topics such as:

- embeddings
- vector database
- prompt engineering
- RAG

When the user asks about one of these topics, the chatbot returns the matching explanation.

Example prompt: `What are embeddings?`

---

### 4. Planner Service

The chatbot includes a simple planner service.

This service returns a short step-by-step study plan when the user asks for a plan, study guide, or checklist.

Example prompt: `Create a study plan for machine learning.`

---

## Routing Logic

The chatbot uses a simple router to decide which service to call based on the user's message:

- **API Service** for questions about SpaceX, launches, or APIs
- **Semantic Search Service** for knowledge-base topics such as embeddings or RAG
- **Planner Service** for study plans or checklists
- **General Chat** for anything else

If a service is selected, its output is passed to the language model, which rewrites it in Professor Byte’s style.

---

## Memory

The chatbot keeps short-term memory using the conversation history provided by Gradio.

Previous user and assistant messages are converted into LangChain message objects and passed into the model so the chatbot can continue the conversation with context.

Because the app uses **Gradio 6-style message history**, the code extracts text from structured message content before sending it to the model.

---

## Guardrails

The chatbot includes simple guardrails.

It refuses requests that try to:

- reveal the **system prompt**
- reveal **hidden instructions**

The chatbot also refuses to discuss the following restricted topics:

- cats
- dogs
- horoscope
- zodiac
- Taylor Swift

---

## Technologies Used

The project uses the following technologies:

- **Python**
- **Gradio** for the chat interface
- **OpenAI API** for language model responses
- **LangChain** for message handling
- **Requests** for external API calls
- **python-dotenv** for loading environment variables

---

## Installation

Install the required Python packages:

```bash
pip install gradio langchain langchain-openai openai requests python-dotenv