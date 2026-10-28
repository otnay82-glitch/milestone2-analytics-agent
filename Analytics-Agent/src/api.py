from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.agent import run_agent
from src.auth import verify_bearer_token
from src.conversation_store import (
    add_message,
    create_conversation,
    get_conversation,
    get_messages,
    init_db,
    list_conversations,
)


app = FastAPI(
    title="Delivery Analytics Agent API",
    version="0.1.0",
)


class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/me")
def me(
    user_id: str = Depends(verify_bearer_token),
) -> dict[str, str]:
    return {"user_id": user_id}


@app.get("/api/v1/conversations")
def conversations(
    user_id: str = Depends(verify_bearer_token),
) -> dict:
    return {
        "conversations": list_conversations(user_id),
    }


@app.post("/api/v1/conversations", status_code=201)
def new_conversation(
    user_id: str = Depends(verify_bearer_token),
) -> dict:
    return create_conversation(user_id)


@app.get("/api/v1/conversations/{conversation_id}")
def conversation_detail(
    conversation_id: str,
    user_id: str = Depends(verify_bearer_token),
) -> dict:
    conversation = get_conversation(conversation_id, user_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Percakapan tidak ditemukan",
        )

    return conversation


@app.post("/api/v1/conversations/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    request: MessageRequest,
    user_id: str = Depends(verify_bearer_token),
) -> dict:
    conversation = get_conversation(conversation_id, user_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Percakapan tidak ditemukan",
        )

    add_message(
        conversation_id,
        user_id,
        "user",
        request.content,
    )

    history = get_messages(
        conversation_id,
        user_id,
        limit=20,
    )

    result = run_agent(
        request.content,
        history,
    )

    add_message(
        conversation_id,
        user_id,
        "assistant",
        result.answer,
    )

    return {
        "conversation_id": conversation_id,
        "answer": result.answer,
        "data_basis": result.data_basis,
        "outcome": result.outcome,
    }