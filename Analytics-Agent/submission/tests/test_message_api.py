import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("DEMO_TOKEN_A")

headers = {
    "Authorization": f"Bearer {token}"
}

# 1. Create conversation
r = requests.post(
    "http://127.0.0.1:8000/api/v1/conversations",
    headers=headers,
)

print("CREATE:", r.status_code)
print(r.text)

conversation_id = r.json()["id"]

# 2. Send message
r = requests.post(
    f"http://127.0.0.1:8000/api/v1/conversations/{conversation_id}/messages",
    headers=headers,
    json={
        "content": "Berapa jumlah shipment per carrier pada Agustus 2026?"
    },
)

print("\nMESSAGE:", r.status_code)
print(r.text)