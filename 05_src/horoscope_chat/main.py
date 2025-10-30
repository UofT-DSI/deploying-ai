from openai import OpenAI
from dotenv import load_dotenv
from horoscope_chat.prompts import return_instructions_root
import json
import requests
from utils.logger import get_logger
import os


_logs = get_logger(__name__)

load_dotenv(".env")
load_dotenv(".secrets")


client = OpenAI()

open_ai_model = os.getenv("OPENAI_MODEL", "gpt-4")

tools = [
    {
        "type": "function",
        "name": "get_horoscope",
        "description": "This tool retrieves the horoscope for an astrological sign for a given day.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "sign": {
                    "type": "string",
                    "description": "An astrological sign like Taurus or Aquarius",
                },
                "date": {
                    "type": "string",
                    "description": 'The date for the horoscope. Accepted values are: Date in format (YYYY-MM-DD) OR "TODAY" OR "TOMORROW" OR "YESTERDAY". If not specified, defaults to "TODAY".',
                    "default": "TODAY"
                }
            },
            "required": ["sign", "date"],
            "additionalProperties": False
        },
        
    },
]



def get_horoscope(sign:str, date:str = "TODAY") -> str:
    """
    An API call to a horoscope service is made.
    The API call is to https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily
    and takes two parameters sign and date.
    Accepted values for sign are: Aries, Taurus, Gemini, Cancer, Leo, Virgo, Libra, Scorpio, Sagittarius, Capricorn, Aquarius, Pisces
    Accepted values for date are: Date in format (YYYY-MM-DD) OR "TODAY" OR "TOMORROW" OR "YESTERDAY".
    """
    
    response = get_horoscope_from_service(sign, date)
    horoscope = get_horoscope_from_response(sign, response)
    return horoscope



def get_horoscope_from_service(sign:str, day:str):
    url = "https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily"
    params = {
        "sign": sign.capitalize(),
        "day": day.upper()
    }
    response = requests.get(url, params=params)
    return response



def get_horoscope_from_response(sign:str, response:requests.Response) -> str:
    resp_dict = json.loads(response.text)
    data = resp_dict.get("data")
    horoscope_data = data.get("horoscope_data", "No horoscope found.")
    date = data.get("date", "No date found.")
    horoscope = f"Horoscope for {sign.capitalize()} on {date}: {horoscope_data}"
    return horoscope


def sanitize_history(history: list[dict]) -> list[dict]:
    clean_history = []
    for msg in history:
        clean_history.append({
            "role": msg.get("role"),
            "content": msg.get("content")
        })
    return clean_history


def horoscope_chat(message: str, history: list[dict] = []) -> str:
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
        tools=tools,
        
    )
    
    conversation_input += response.output

    # Handle function calls if any
    for item in response.output:
        if item.type == "function_call":
            if item.name == "get_horoscope":
                args = json.loads(item.arguments)
                _logs.info(f'Function call args: {args}')
                
                # Call the horoscope function
                horoscope_result = get_horoscope(**args)
                
                # Add function call result to conversation
                
                func_call_output = {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({
                        "horoscope": horoscope_result
                    })
                }
                
                _logs.debug(f"Function call output: {func_call_output}")

                conversation_input = conversation_input + [func_call_output]
                
                # Make second API call with function result
                response = client.responses.create(
                    model=open_ai_model,
                    instructions=instructions,
                    tools=tools,
                    input=conversation_input
                )
                break
    
    
    return response.output_text
