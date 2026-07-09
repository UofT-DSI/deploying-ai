# Assignment 2: Conversational AI System

## Project Overview

This project implements a chat-based AI assistant called **Radiography Study Buddy**.

The assistant is designed to help users study basic dental radiography concepts in a friendly and simple way. It uses a conversational interface and provides three services.

## Chatbot Personality

The chatbot acts as a supportive study assistant. Its tone is clear, friendly, and encouraging. It explains technical concepts in simple language and helps users practice with short questions.

## Services

### Service 1: API Service

This service uses a public API as its backend. The chatbot can retrieve information from an external API and rewrite the result in a natural and user-friendly way instead of copying the API response directly.

### Service 2: Semantic Query Service

This service allows users to ask questions about a small dental radiography knowledge base. The system searches the knowledge base semantically and returns the most relevant answer.

### Service 3: Study Helper Service

This service provides study support, such as short explanations, quiz-style questions, and simple review prompts.

## User Interface

The chatbot uses a Gradio chat interface. The interface allows users to type messages and receive conversational responses.

## Memory

The system keeps short-term memory during the chat session by storing recent conversation history. This allows the chatbot to respond more naturally during the conversation.

## Guardrails

The chatbot includes guardrails to prevent users from:

- Accessing or revealing the system prompt
- Modifying the system prompt
- Asking about restricted topics

Restricted topics include:

- Cats or dogs
- Horoscopes or Zodiac signs
- Taylor Swift

## Implementation Location

The project files are implemented in:

`./05_src/assignment_chat`

## Files

- `app.py`: main chat interface and application logic
- `services.py`: service functions
- `knowledge_base.py`: small custom knowledge base for semantic search
- `README.md`: project explanation

## API Implementation Decision

For the API service, I used a public Wikipedia API and Python's built-in urllib and json libraries. I avoided installing new libraries to stay within the course environment requirem
