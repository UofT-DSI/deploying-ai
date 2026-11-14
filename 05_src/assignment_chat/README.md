# FitCoach AI – Personal Fitness Assistant

## Project Overview

FitCoach AI is an AI-powered conversational assistant designed to help users with fitness, exercise, muscle growth, recovery, and nutrition.

The assistant provides practical fitness information through three integrated services: a nutrition API, semantic search, and a workout calculation tool.

It uses a friendly and professional personality, supports conversation history, and includes guardrails to protect its instructions and restrict unrelated topics.

## Architecture

The application is built using Python, LangChain, LangGraph, Gradio, and ChromaDB.

### 1. Nutrition API – USDA FoodData Central

The assistant connects to the USDA FoodData Central API to retrieve nutritional information about foods.

It provides:
- Calories
- Protein
- Carbohydrates
- Fat

The API results are transformed into a clear and readable response rather than returned directly to the user.

### 2. Semantic Search – ChromaDB

A fitness knowledge base contains information about:
- Muscle growth
- Protein and muscle recovery
- Rest and recovery
- Warm-up
- Strength training
- Hydration

The documents are converted into embedding vectors using the `text-embedding-3-small` model.

ChromaDB stores the documents and their embeddings persistently in the local `chroma_db` directory.

When a user asks a fitness question, the system converts the query into an embedding and retrieves relevant documents using semantic similarity.

The retrieved information is then used by the language model to generate an answer.

### 3. Function Calling – Workout Volume Calculator

The assistant provides a workout volume calculator through function calling.

It calculates training volume using:

`Sets × Repetitions × Weight`

For example:

`4 sets × 12 reps × 20 kg = 960 kg`

The language model decides when to call this tool based on the user's request.

## Chat Interface

The application uses Gradio's ChatInterface to provide a conversational user experience.

Features include:
- Interactive chat interface
- Conversation history
- Integration with all three services
- Responses in the same language as the user

## Personality and Guardrails

FitCoach AI is designed to be friendly, supportive, practical, and professional.

It includes guardrails that:
- Refuse questions about cats and dogs.
- Refuse questions about horoscopes and zodiac signs.
- Refuse questions about Taylor Swift.
- Reject common attempts to reveal or modify the system prompt.
- Keep responses focused on fitness, exercise, recovery, and nutrition.

The assistant also