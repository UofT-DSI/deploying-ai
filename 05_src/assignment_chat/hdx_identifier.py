import requests

BASE = "https://hapi.humdata.org/api/v2"

r = requests.get(
    f"{BASE}/encode_app_identifier",
    params={
        "application": "assignment_chat",
        "email": "your.real.email@domain.com"  
    },
    timeout=20
)

print("status:", r.status_code)
print(r.json())