"""Starter UI for the participant's delivery analytics API."""

from __future__ import annotations

import os

import httpx
import streamlit as st


API_URL = os.getenv("AGENT_API_URL", "http://localhost:8000").rstrip("/")
SELECTOR_KEY = "conversation_picker_v2"


def api_request(method: str, path: str, token: str, **kwargs: object) -> dict | None:
    try:
        response = httpx.request(
            method,
            f"{API_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=35,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", "Permintaan gagal")
        except ValueError:
            detail = "Permintaan gagal"
        st.error(f"API {exc.response.status_code}: {detail}")
    except (httpx.RequestError, ValueError):
        st.error("Backend tidak tersedia atau respons tidak valid.")
    return None


st.set_page_config(
    page_title="Agent Analitik Pengiriman",
    page_icon="📦",
)
st.title("Agent Analitik Pengiriman")
st.caption(
    "Fakta analitik berasal dari Neon Gold. "
    "Percakapan demo disimpan oleh backend."
)

token = st.sidebar.text_input("Bearer token demo", type="password")

# Reset the selected conversation when the token changes.
if st.session_state.get("active_token") != token:
    st.session_state["active_token"] = token
    st.session_state["conversation_id"] = None
    st.session_state.pop(SELECTOR_KEY, None)
    st.session_state.pop("last_basis", None)

if not token:
    st.info("Masukkan token demo yang diberikan penyelenggara.")
    st.stop()

# Create a new conversation and select it immediately.
if st.sidebar.button("Percakapan baru"):
    created = api_request(
        "POST",
        "/api/v1/conversations",
        token,
        json={},
    )
    if created and created.get("id"):
        new_id = created["id"]
        st.session_state["conversation_id"] = new_id
        st.session_state[SELECTOR_KEY] = new_id
        st.rerun()

# Load the conversation list without automatically selecting the first item.
listing = api_request("GET", "/api/v1/conversations", token)
conversations = listing.get("conversations", []) if listing else []
ids = [item["id"] for item in conversations]

if ids:
    current = st.session_state.get("conversation_id")

    # Keep the current selection only if it still exists.
    if current not in ids:
        current = None
        st.session_state["conversation_id"] = None

    # The new selector starts empty unless a conversation was explicitly selected.
    if st.session_state.get(SELECTOR_KEY) not in ids:
        st.session_state[SELECTOR_KEY] = current

    selected = st.sidebar.selectbox(
        "Percakapan saya",
        ids,
        index=(
            ids.index(st.session_state[SELECTOR_KEY])
            if st.session_state.get(SELECTOR_KEY) in ids
            else None
        ),
        placeholder="Pilih percakapan...",
        format_func=lambda value: next(
            (
                item.get("title") or value
                for item in conversations
                if item["id"] == value
            ),
            value,
        ),
        key=SELECTOR_KEY,
    )

    st.session_state["conversation_id"] = selected
else:
    st.session_state["conversation_id"] = None
    st.info("Belum ada percakapan. Klik 'Percakapan baru' untuk mulai.")

conversation_id = st.session_state.get("conversation_id")

if conversation_id:
    detail = api_request(
        "GET",
        f"/api/v1/conversations/{conversation_id}",
        token,
    )

    if detail:
        for message in detail.get("messages", []):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        basis = st.session_state.get("last_basis", {}).get(conversation_id)
        if basis:
            st.caption(f"Dasar data jawaban terakhir: {basis}")

    prompt = st.chat_input(
        "Tanya tentang volume, SLA, refund, carrier, atau kota"
    )

    if prompt:
        result = api_request(
            "POST",
            f"/api/v1/conversations/{conversation_id}/messages",
            token,
            json={"content": prompt},
        )
        if result:
            st.session_state.setdefault("last_basis", {})[
                conversation_id
            ] = result.get("data_basis", "")
            st.rerun()
else:
    st.info("Pilih percakapan lama atau klik 'Percakapan baru' untuk mulai.")
