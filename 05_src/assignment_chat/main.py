from openai import OpenAI
from dotenv import load_dotenv
from assignment_chat.prompts import return_instructions_root  # need to be replaced
import json
import requests
from utils.logger import get_logger
import os


_logs = get_logger(__name__)

load_dotenv(".env")
load_dotenv(".secrets")


client = OpenAI()

open_ai_model = os.getenv("OPENAI_MODEL", "gpt-4")
IPSTACK_API_KEY = os.getenv("IP_STACK_KEY")

tools = [ #need to be replaced
    {
        "type": "function",
        "name": "get_ipstack_location",
        "description": "This tool retrieves the location of a user based on their IP address.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "ip": {
                    "type": "string",
                    "description": "The IP address of the user.",
                }  
            },
            "required": ["ip"],
            "additionalProperties": False
        },
        
    },
]



def get_ipstack_location(ip: str) -> dict:
    """
   Calls IPStack API and returns structured geolocation information based on the provided IP address
    """
    
    response = get_ipstack_from_service(ip)
    location = get_ipstack_from_response(ip, response)
    return location



def get_ipstack_from_service(ip:str):
    """
    Calls the IPStack API with the provided IP address and returns the raw response."""
    url = f"http://api.ipstack.com/{ip}"
    params = {
        "access_key": IPSTACK_API_KEY
    }
    response = requests.get(url, params=params)
    return response



def get_ipstack_from_response(ip:str, response: requests.Response) -> dict:
    """
    Extracts and formats the API Stack response.
    """
    if response.status_code == 200:
        data = response.json()
        location_info = {
            "ip": ip,
            "city": data.get("city"),
            "region": data.get("region_name"),
            "country": data.get("country_name"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude")
        }
        return location_info
    else:
       
        return {
            "ip": ip,
            "error": f"Failed to retrieve location. Status code: {response.status_code}"
        }

def sanitize_history(history: list[dict]) -> list[dict]:
    clean_history = []
    for msg in history:
        clean_history.append({
            "role": msg.get("role"),
            "content": msg.get("content")
        })
    return clean_history


def ipstack_chat(message: str, history: list[dict] = []) -> str:
    """
    Chat flow
    """
    _logs.info(f'User message: {message}')
    
    instructions = return_instructions_root()
    
    user_msg = {
        "role": "user",
        "content": message
    }
    
    conversation_input = sanitize_history(history) + [user_msg]
    
    #First OpenAI Call
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
            if item.name == "get_ipstack_location":
                args = json.loads(item.arguments)
                _logs.info(f'Function call args: {args}')
                
                # Call the ipstack function
                ipstack_result = get_ipstack_location(**args)
                
                # Add function call result to conversation
                
                func_call_output = {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({
                        "location": ipstack_result
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
