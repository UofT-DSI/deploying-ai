from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()
load_dotenv('.secrets')
from  utils.logger import get_logger

_logs = get_logger(__name__)

client = OpenAI()

mcp_url=os.getenv('MCP_URL')
_logs.info(f'MCP URL: {mcp_url}')
resp = client.responses.create(
    model="gpt-5",
    tools=[
        {
            "type": "mcp",
            "server_label": "weather_server",
            "server_description": "A weather server that returns weather information.",
            "server_url": mcp_url,
            "require_approval": "never",
        },
    ],
    input="What is the weather?",
)

print(resp.output_text)