import sys
import os
import openai

from dotenv import load_dotenv
import os

src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(src_dir, ".env"))
load_dotenv(os.path.join(src_dir, ".secrets"))

print("API key:", os.getenv("API_GATEWAY_KEY", "NOT FOUND"))

sys.path.insert(0, ".")
from services.bank_holidays_service import get_holidays_in_range

result = get_holidays_in_range("Scotland", "2026-01-01", "2026-06-30")
print(result)

#######################################
from config import client, CHAT_MODEL
print("Client:", client)
print("Chat model:", CHAT_MODEL)

response = client.responses.create(
    model=CHAT_MODEL,
    input="Say hello in one sentence."
)
if hasattr(response, "output_text"):
    print(response.output_text)
else:
    print("No output_text in response:", response)

###################################

