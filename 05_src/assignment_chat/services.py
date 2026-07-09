"""
Services for Assignment 2 chatbot.

This file contains three services:
1. API service
2. Semantic query service
3. Study helper / quiz service
"""

import json
import urllib.parse
import urllib.request
from knowledge_base import KNOWLEDGE_BASE


# -----------------------------
# Service 1: API Service
# -----------------------------

def api_service(topic):
    """
    Uses Wikipedia public API to retrieve a short summary.
    The response is rewritten in a simple and friendly way.
    """

    if not topic.strip():
        return "Please give me a topic to look up."

    encoded_topic = urllib.parse.quote(topic.strip())
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_topic}"

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "RadiographyStudyBuddy/1.0"
            }
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        extract = data.get("extract", "")
        title = data.get("title", topic)

        if not extract:
            return (
                f"I connected to the API, but I could not find a useful summary for '{topic}'. "
                "Try a more general topic, such as 'radiography' or 'dental radiography'."
            )

        short_extract = extract[:700]

        return (
            f"Here is a simple API-based summary about **{title}**:\n\n"
            f"{short_extract}\n\n"
            "I rewrote the API result as a short study-friendly explanation."
        )

    except Exception as error:
        return (
            "Sorry, I could not retrieve information from the API right now. "
            f"Technical note: {type(error).__name__}. "
            "Try a simpler topic such as 'radiography'."
        )


# -----------------------------
# Service 2: Semantic Query Service
# -----------------------------

def semantic_query_service(user_question):
    """
    Searches the custom dental radiography knowledge base.
    This simple version uses keyword overlap as a lightweight retrieval method.
    """

    question_words = set(user_question.lower().split())

    best_score = 0
    best_item = None

    for item in KNOWLEDGE_BASE:
        text = (item["topic"] + " " + item["text"]).lower()
        text_words = set(text.split())

        score = len(question_words.intersection(text_words))

        if score > best_score:
            best_score = score
            best_item = item

    if best_item is None or best_score == 0:
        return (
            "I could not find a strong match in my radiography knowledge base. "
            "Try asking about bitewing, panoramic radiography, paralleling technique, "
            "bisecting angle technique, image quality, radiation safety, or quality assurance."
        )

    return (
        f"Based on my study knowledge base, the most relevant topic is "
        f"**{best_item['topic']}**.\n\n"
        f"{best_item['text']}"
    )


# -----------------------------
# Service 3: Study Helper / Quiz Service
# -----------------------------

def study_helper_service(user_message):
    """
    Provides study support such as quiz questions and short review prompts.
    """

    message = user_message.lower()

    if "quiz" in message or "test me" in message:
        return (
            "Here is a short quiz for you:\n\n"
            "1. What is the main purpose of bitewing radiographs?\n"
            "2. Why is the paralleling technique usually preferred?\n"
            "3. Does a panoramic radiograph replace detailed intraoral radiographs?\n"
            "4. What does the ALARA principle mean in radiation safety?\n\n"
            "Try answering these, and I can help you review your answers."
        )

    if "explain" in message or "study" in message or "review" in message:
        return (
            "Here is a quick study tip:\n\n"
            "When studying dental radiography, focus on three things: "
            "the purpose of each image type, the correct technique, and radiation safety. "
            "These areas often appear in exams and clinical practice."
        )

    return (
        "I can help you study dental radiography. "
        "You can ask me to explain a topic, quiz you, or review key concepts."
    )


# -----------------------------
# Guardrails
# -----------------------------

def check_guardrails(user_message):
    """
    Blocks restricted topics and attempts to reveal or change the system prompt.
    """

    blocked_topics = [
        "cat", "cats", "dog", "dogs",
        "horoscope", "horoscopes", "zodiac",
        "taylor swift"
    ]

    lower_message = user_message.lower()

    if "system prompt" in lower_message:
        return "I cannot reveal or modify the system prompt."

    if "change your instructions" in lower_message:
        return "I cannot reveal or modify the system prompt."

    for topic in blocked_topics:
        if topic in lower_message:
            return "Sorry, I cannot respond to that restricted topic."

    return None


# -----------------------------
# Router
# -----------------------------

def route_message(user_message):
    """
    Decides which service should respond to the user.
    """

    guardrail_response = check_guardrails(user_message)
    if guardrail_response:
        return guardrail_response

    lower_message = user_message.lower()

    if lower_message.startswith("api:"):
        topic = user_message.replace("api:", "").strip()
        return api_service(topic)

    if "quiz" in lower_message or "test me" in lower_message or "study" in lower_message:
        return study_helper_service(user_message)

    return semantic_query_service(user_message)
