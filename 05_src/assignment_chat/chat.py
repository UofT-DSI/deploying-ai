import gradio as gr
import requests

# Guardrails: restricted topics
restricted_topics = [
    "cat",
    "dog",
    "horoscope",
    "zodiac",
    "taylor swift"
]

# Semantic knowledge base
knowledge = {
    "rag": "RAG stands for Retrieval Augmented Generation. It combines information retrieval with language generation.",
    "embedding": "Embeddings convert text into numerical vectors that capture semantic meaning.",
    "semantic search": "Semantic search retrieves documents based on meaning rather than exact keyword matches."
}

# Service 1: API
def get_quote():
    try:
        url = "https://api.quotable.io/random"
        r = requests.get(url, timeout=10)
        data = r.json()
        quote = data.get("content", "Stay curious.")
        author = data.get("author", "Unknown")
        return f"Inspirational quote: '{quote}' — {author}"
    except Exception:
        return "I could not reach the quote API right now, but here is one: 'Stay curious and keep learning.'"

# Service 3: Tool
def word_count(text):
    words = text.split()
    return f"This sentence has {len(words)} words."

def chat(message, history):

    msg = message.lower().strip()

    # Guardrails
    if any(topic in msg for topic in restricted_topics):
        return "Sorry, my programming forbids me from discussing that topic."

    if "system prompt" in msg or "ignore previous instructions" in msg:
        return "Nice try, but I cannot reveal or modify my system instructions."

    # Service 1: API
    if "quote" in msg:
        return get_quote()

    # Service 3: Tool
    if "count" in msg:
        return word_count(message)

    # Service 2: Semantic Query
    for key, value in knowledge.items():
        if key in msg:
            return value

    # Personality + memory
    if len(history) == 0:
        return "Hello! I'm your AI Study Buddy. I can explain AI concepts, count words, or give inspirational quotes."

    return "I'm not sure about that. Try asking me about RAG, embeddings, semantic search, quotes, or word counting."

demo = gr.ChatInterface(
    fn=chat,
    title="AI Study Buddy 🤖",
    description="A friendly assistant that explains AI concepts, gives quotes, and performs simple tools."
)

demo.launch()
