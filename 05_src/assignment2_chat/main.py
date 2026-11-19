from email.mime import message

from openai import OpenAI
from dotenv import load_dotenv
from assignment2_chat.prompts import return_instructions_root
from assignment2_chat.tools_alva import search_alva_knowledge
import json
import requests
from utils.logger import get_logger
import os


_logs = get_logger(__name__)

load_dotenv(".env")
load_dotenv(".secrets")


# Connect to the DSI API gateway
client = OpenAI(
    api_key="any value",
    base_url="https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1",
    default_headers={
        "x-api-key": os.getenv("API_GATEWAY_KEY")
    }
)

open_ai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

news_api_key = os.getenv("NEWS_API_KEY")

tools = [
    {
        "type": "function",
        "name": "get_ai_workforce_news",
        "description": "This tool retrieves the latest news and trends related to AI in the workforce and AI readiness challenges.",
        "strict": True,
        
        "parameters": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "User's workplace role."
                },
                "topic": {
                    "type": "string",
                    "description": "AI workforce topic."
                },
                "challenge": {
                    "type": "string",
                    "description": "AI readiness concern."
                }
            },
            "required": ["role", "topic", "challenge"],
            "additionalProperties": False
        }
    },

    #Service 2 - ChromaDB semantic search
{
"type": "function",
"name": "search_alva_knowledge",
"description": "Search AI workforce readiness guidance.",
"strict": True,
"parameters": {
"type": "object",
"properties": {
"query": {
"type": "string",
"description": "User's question about AI readiness."
}
},
"required": ["query"],
"additionalProperties": False
}
},

# Service 3 - AI readiness recommendations
{
    "type": "function",
    "name": "generate_ai_readiness_recommendation",
    "description": "Generate an AI readiness action plan.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "description": "User's workplace role."
            },
            "challenge": {
                "type": "string",
                "description": "User's AI adoption challenge."
            }
        },
        "required": ["role", "challenge"],
        "additionalProperties": False
    }
}

]


def get_ai_workforce_news(
        role:str,
        topic:str,
        challenge:str
    ) -> str:
    
    """
    Retrieves current AI trends from a news API and
    returns a summarized response.
    """

    response = get_ai_workforce_news_from_service(role, topic, challenge)

    news = get_ai_workforce_news_from_response(role, topic, challenge, response)

    return news



def get_ai_workforce_news_from_service(
        role:str,
        topic:str,
        challenge:str
    ) -> requests.Response:

    url = "https://newsapi.org/v2/everything"

    params = {
        "q": f"{topic} {challenge}",
        "language": "en",
        "pageSize": 5,
        "apiKey": news_api_key
    }

    response = requests.get(
        url,
        params=params
    )

    return response



def get_ai_workforce_news_from_response(
        role:str,
        topic:str,
        challenge:str,
        news_response:requests.Response
    ) -> str:
    news_data = news_response.json()
    response = f"""
Role:
{role}

Topic:
{topic}

Challenge:
{challenge}

Potential Barriers:
- Limited AI literacy
- Low confidence using AI tools
- Unclear organizational expectations

Recommendations:
- Provide AI fundamentals training
- Create AI champions
- Start with small pilot projects
- Share successful AI use cases

Expected Outcome:
Improved workforce readiness and AI adoption.
"""
    response += "\nRecent AI Workforce News:\n"

    for article in news_data.get("articles", []):

     response += f"""

Title: {article.get("title")}

Published: {article.get("publishedAt")}

Description: {article.get("description")}

URL: {article.get("url")}

"""

    return response

# Service 3 - Personalized action plan
def generate_ai_readiness_recommendation(
    role: str,
    challenge: str
) -> str:

    recommendation = f"""
AI Workforce Readiness Action Plan

Role: {role}
Challenge: {challenge}

Recommended Actions:
1. Assess current AI knowledge and skills.
2. Provide basic AI literacy training.
3. Identify AI champions within the team.
4. Pilot AI tools in low-risk tasks.
5. Gather feedback and monitor progress.

Expected Outcome:
Improved workforce AI readiness and adoption.
"""
    return recommendation


def extract_text_content(content) -> str:
    """
    Gradio's Chatbot normalizes string content into a list of parts like
    [{"type": "text", "text": "..."}], which the Responses API does not accept
    as-is. Flatten back down to plain text.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return "" if content is None else str(content)


def sanitize_history(history: list[dict]) -> list[dict]:
    clean_history = []
    for msg in history:
        clean_history.append({
            "role": msg.get("role"),
            "content": extract_text_content(msg.get("content"))
        })
    return clean_history


def alva_chat(message: str, history: list[dict] = []) -> str:
    _logs.info(f'User message: {message}')
    instructions = return_instructions_root()
    user_msg = {
        "role": "user",
        "content": message
        }
    conversation_input = sanitize_history(history) + [user_msg]
    response = client.responses.create(
        model=open_ai_model,
        instructions=instructions,
        input=conversation_input,
        tools=tools
 
    )

    conversation_input += response.output

    # Handle function calls if any
    for item in response.output:

        if item.type == "function_call":
            _logs.info(f"Alva selected tool: {item.name}")
            # Service 1: AI Workforce News
            if item.name == "get_ai_workforce_news":

                args = json.loads(item.arguments)
                news_result = get_ai_workforce_news(**args)

                func_call_output = {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({
                        "news": news_result
                    })
                }

                _logs.info(f"Function call output: {func_call_output}"
                )

                conversation_input += [func_call_output]

                response = client.responses.create(
                    model=open_ai_model,
                    instructions=instructions,
                    tools=tools,
                    input=conversation_input,
                    tool_choice="none"
                )
                break

            # Service 2: ChromaDB Semantic Search
            elif item.name == "search_alva_knowledge":

                args = json.loads(item.arguments)
                knowledge_result = search_alva_knowledge(**args)

                func_call_output = {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({
                        "knowledge": [
                            result.model_dump()
                            for result in knowledge_result
                        ]
                    })
                }

                _logs.info(f"Function call output: {func_call_output}"
                )

                conversation_input += [func_call_output]

                response = client.responses.create(
                    model=open_ai_model,
                    instructions=instructions,
                    tools=tools,
                    input=conversation_input,
                    tool_choice="none"
                )
                break

            # Service 3: AI Readiness Recommendations
            elif item.name == "generate_ai_readiness_recommendation":

                args = json.loads(item.arguments)

                recommendation_result = (
                    generate_ai_readiness_recommendation(**args)
                )

                func_call_output = {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({
                        "recommendation": recommendation_result
                    })
                }

                _logs.info(f"Function call output: {func_call_output}"
                )

                conversation_input += [func_call_output]

                response = client.responses.create(
                    model=open_ai_model,
                    instructions=instructions,
                    tools=tools,
                    input=conversation_input,
                    tool_choice="none"
                )
                break

    return response.output_text
