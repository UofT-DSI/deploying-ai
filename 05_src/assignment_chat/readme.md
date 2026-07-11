# AI Study Buddy

AI Study Buddy is an AI learning assistant designed to explain AI concepts, answer questions using semantic search, create quizzes, and retrieves programming insights from an external API. 

## Services
- **Programming Wisdom** Retrieves a programming quote from the GitHub Zen API and explains the relevance.
- **AI Knowledge Search:** Uses ChromaDB semantic search to answer AI-related questions.
- **Study Quiz:** Generates short quizzes on AI topics.

## Implementation
- Built with LangGraph and a Gradio chat interface.
- System instructions are stored in `prompts.py`.
- Tools are implemented in `tools.py`.
- Guardrails prevent revealing the system prompt and block the required restricted topics.
