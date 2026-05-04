import gradio as gr
import requests
import chromadb

# Create persistent DB
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="photography_notes")

# Guardrails
RESTRICTED_TOPICS = [
    "cat", "cats",
    "dog", "dogs",
    "horoscope", "horoscopes",
    "zodiac",
    "taylor swift"
]

PROMPT_ATTACKS = [
    "system prompt",
    "ignore previous instructions",
    "reveal your instructions",
    "modify your system prompt"
]

def check_guardrails(message):
    text = message.lower()

    for topic in RESTRICTED_TOPICS:
        if topic in text:
            return "Sorry, I cannot answer questions about that topic."

    for attack in PROMPT_ATTACKS:
        if attack in text:
            return "Sorry, I cannot reveal or modify my system instructions."

    return None


# Load dataset into ChromaDB
def load_notes():
    with open("data/photography_knowledge.txt", "r") as file:
        notes = file.read().split("\n\n")

    if collection.count() == 0:
        for i, note in enumerate(notes):
            collection.add(documents=[note], ids=[str(i)])


# Weather API service
def get_weather(city):
    try:
        url = f"https://wttr.in/{city}?format=j1"
        response = requests.get(url, timeout=10)
        data = response.json()

        current = data["current_condition"][0]
        temp = current["temp_C"]
        condition = current["weatherDesc"][0]["value"]

        return f"In {city}, it is {temp}°C with {condition}. This helps plan outdoor shoots."

    except:
        return "Could not fetch weather. Try again."


# Semantic search service
def search_notes(question):
    results = collection.query(
        query_texts=[question],
        n_results=2
    )

    docs = results["documents"][0]

    answer = "From my photography notes:\n\n"
    for doc in docs:
        answer += f"- {doc}\n"

    return answer


# Custom service (shoot planner)
def create_plan():
    return (
        "Here is a simple photoshoot plan:\n\n"
        "1. Start with candid shots\n"
        "2. Take posed portraits\n"
        "3. Capture details\n"
        "4. Use good lighting (golden hour if possible)\n"
        "5. End with group photos"
    )


# Chat function
def chat(message, history):
    blocked = check_guardrails(message)
    if blocked:
        return blocked

    text = message.lower()

    if "weather" in text:
        city = text.replace("weather", "").strip()
        if city == "":
            city = "Toronto"
        return get_weather(city)

    elif "plan" in text or "photoshoot" in text:
        return create_plan()

    else:
        return search_notes(message)


# Load data
load_notes()

# UI
demo = gr.ChatInterface(
    fn=chat,
    title="My Outdoor Photoshoot Assistant",
    description="I use this to quickly plan outdoor photoshoots, check weather, and recall my photography notes."
)

demo.launch()