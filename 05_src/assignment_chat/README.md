## Travel Planner AI
The chat client is designed as a professional AI travel planning assistant that helps users plan trips by combining real-time information, stored travel knowledge, and planning tools.

The assistant uses a helpful, informative, and structured tone, similar to a professional travel consultant.
It focuses on providing clear recommendations, practical advice, and organized travel plans rather than casual conversation.

The assistant maintains memory throughout the conversation to keep track of the user’s travel preferences, such as destination, budget, number of days, and interests, so that future responses can build on earlier messages.

The assistant also includes guardrails that prevent the user from accessing the system prompt or modifying the assistant’s behavior, and it refuses to respond to restricted topics such as cats, dogs, horoscopes, zodiac signs, and Taylor Swift.

## Personality



## Services 

This system implements three services as required by the assignment.

Service 1 — API-Based Service

Example queries handled by this service:

"What will the weather be like in Paris this weekend?"
"Do I need a jacket in Tokyo next week?"

The API response is transformed into a conversational explanation before being shown to the user.

Service 2 — Semantic Query Service

This service allows the user to ask questions that are answered using semantic search over a custom travel knowledge base.

Example queries handled by this service:

"What are good things to do in Rome for 3 days?"
"Is Barcelona expensive for tourists?"
"What areas should I stay in Tokyo?"

This service demonstrates retrieval-augmented generation using persistent vector storage.

Service 3 — Tool-Based Service (Function Calling)

The third service uses function calling to provide structured travel planning tools.

Several planning tools are implemented as functions that the model can call when the user requests calculations or structured planning.

The tools include:

Budget planner
Calculates how a travel budget should be divided between lodging, food, transportation, and activities.

Itinerary generator
Creates a day-by-day travel plan based on the destination, number of days, and user preferences.

Packing list generator
Generates a packing list based on the destination, weather conditions, and activities.

The model decides when to call these tools and uses their output to generate a natural language response.

Example queries handled by this service:

"Plan a 3 day trip to New York"
"I have a $1000 budget for 5 days in Italy"
"What should I pack for a trip to Iceland?"

This service demonstrates the use of function calling to extend the capabilities of the chat system.

# Implementation Decisions

The system is implemented as a chat-based interface using Gradio.

The main design goal was to create a modular conversational AI system where different types of user requests are routed to different services.

The system follows this structure:

The user message is received through the Gradio chat interface.

Guardrails check the message for restricted topics or attempts to reveal the system prompt.

The message is analyzed to determine which service should handle the request.

The appropriate service is called:

API service for real-time data

Semantic search service for knowledge retrieval

Tool service for calculations or structured planning

The result is passed to the language model to produce a natural response.

The conversation history is stored to maintain memory across turns.

Conversation memory is stored in a list of messages that is passed to the model on each request.
If the conversation becomes too long, older messages can be summarized to keep the context within the model’s limits.

ChromaDB is used with file persistence so the semantic search database does not need to be rebuilt each time the program runs.

The project was implemented using only the libraries available in the course environment.