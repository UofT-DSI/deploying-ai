import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# 1. Load secrets from 05_src
secrets_path = Path(__file__).resolve().parent.parent / ".secrets"

load_dotenv(secrets_path)

# 2. Get API key
GO_API_KEY = os.getenv("GO_API_KEY")

print("Secrets file exists:", secrets_path.exists())
print("GO API Key loaded:", bool(GO_API_KEY))

if not GO_API_KEY:
    raise ValueError("Missing GO_API_KEY")

# 3. GO Transit API endpoint
url = (
    "https://api.openmetrolinx.com/"
    "OpenDataAPI/api/V1/Gtfs/Feed/VehiclePosition"
)

# 4. Send request
print("Connecting to GO Transit API...", flush=True)

try:
    response = requests.get(
        url,
        params={"key": GO_API_KEY},
        timeout=15,
        allow_redirects=False
    )

    print("Status Code:", response.status_code)
    print("Content Type:", response.headers.get("Content-Type"))
    print("Response Size:", len(response.content), "bytes")
    print("Response Preview:", response.content[:200])

except requests.exceptions.Timeout:
    print("ERROR: GO Transit API request timed out.")

except requests.exceptions.ConnectionError as e:
    print("ERROR: Cannot connect to GO Transit API.")
    print(str(e))

except requests.exceptions.RequestException as e:
    print("ERROR:", str(e))

    print("Status Code:", response.status_code)
    print("Content Type:", response.headers.get("Content-Type"))

    response.raise_for_status()

    print("Response size:", len(response.content), "bytes")
    print("Response preview:", response.content[:200])

except requests.exceptions.RequestException as e:
    print("API Error:", e)

