import os

from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()

import os

from fastapi import Header, HTTPException


def verify_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token tidak valid")

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Token tidak valid")

    token_users = {
        os.getenv("DEMO_TOKEN_A", ""): "user_a",
        os.getenv("DEMO_TOKEN_B", ""): "user_b",
    }

    user_id = token_users.get(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Token tidak valid")

    return user_id