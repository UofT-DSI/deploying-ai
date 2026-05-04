# KindGuide  – Chat-Based AI Assistant

## Overview

KindGuide is a chat-based AI assistant built using the OpenAI API and Gradio. It is designed as a polite, humble, and uplifting guide that interacts with users in a warm and encouraging tone. The system integrates multiple services, maintains conversational memory, and enforces guardrails to ensure safe and controlled interactions.



## Features

### 1. Chat Interface

* Built using Gradio’s ChatInterface
* Maintains conversation history (short-term memory)
* Provides a friendly and engaging user experience

### 2. Personality

* The assistant ("KindGuide") is:

  * Polite and humble
  * Encouraging and positive
  * Focused on making the user feel better



## Services

### 1. OpenAI Chat Service

* Handles general conversation using the OpenAI API
* Uses a system prompt to define personality and behavior

### 2. External API Service (ZenQuotes)

* Fetches random quotes from: https://zenquotes.io/api/random
* Transforms quotes into uplifting, human-friendly messages using the OpenAI API

### 3. Utility Logic (Routing + Memory)

* Routes user queries to the appropriate service
* Maintains conversation history for contextual responses



## Guardrails

The system includes safeguards to ensure safe and controlled usage:

### 1. Prompt Protection

* Prevents users from accessing or modifying the system prompt
* Blocks phrases like:

  * "system prompt"
  * "change your role"
  * "act as"

### 2. Restricted Topics

The assistant does not respond to queries related to:

* Cats or dogs
* Horoscopes or zodiac signs
* Taylor Swift

If such topics are detected, the assistant politely declines and redirects the conversation.



## Design Decisions

* **Gradio** was chosen for its simplicity in building chat interfaces
* **ZenQuotes API** was used as a lightweight external API for motivation-based responses
* **Short-term memory** was implemented using chat history to maintain context
* **Keyword-based routing** was used for simplicity and clarity



## How to Run

1. Install dependencies:

   ```bash
   pip install openai gradio requests
   ```

2. Set your OpenAI API key:

   ```bash
   export OPENAI_API_KEY="your_api_key_here"
   ```

3. Run the application:

   ```bash
   python app.py
   ```



## Example Usage

* "Motivate me" → Returns an uplifting message based on a quote
* "I feel stressed" → Provides a supportive response
* Restricted queries → Politely declined



## Future Improvements

* Add more external APIs (e.g., weather, news)
* Improve routing using LLM-based intent detection
* Implement advanced memory summarization


## Conclusion

KindGuide demonstrates how to combine LLMs, external APIs, and UI frameworks into a safe, engaging, and functional conversational system.
