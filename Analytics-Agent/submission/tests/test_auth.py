import os
from fastapi.testclient import TestClient

from src.api import app

TOKEN_A = os.getenv("DEMO_TOKEN_A")
TOKEN_B = os.getenv("DEMO_TOKEN_B")

assert TOKEN_A, "DEMO_TOKEN_A belum tersedia"
assert TOKEN_B, "DEMO_TOKEN_B belum tersedia"


def auth(token):
    return {"Authorization": f"Bearer {token}"}


with TestClient(app) as client:
    # 1. User A membuat conversation
    r = client.post(
        "/api/v1/conversations",
        headers=auth(TOKEN_A),
        json={"title": "Authorization Test"},
    )
    print("CREATE A:", r.status_code)
    assert r.status_code == 201

    conversation_id = r.json()["id"]

    # 2. User A boleh membaca conversation miliknya
    r = client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=auth(TOKEN_A),
    )
    print("A READ OWN:", r.status_code)
    assert r.status_code == 200

    # 3. User B tidak boleh membaca conversation User A
    r = client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=auth(TOKEN_B),
    )
    print("B READ A:", r.status_code)
    assert r.status_code == 404

    # 4. User B tidak boleh mengirim message ke conversation User A
    r = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=auth(TOKEN_B),
        json={"content": "Unauthorized access test"},
    )
    print("B WRITE A:", r.status_code)
    assert r.status_code == 404

    # 5. Tanpa token harus 401
    r = client.get(f"/api/v1/conversations/{conversation_id}")
    print("NO TOKEN:", r.status_code)
    assert r.status_code == 401

print("=" * 60)
print("PASS: conversation ownership & bearer authorization")