import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY belum dikonfigurasi"
        )

    return OpenAI(api_key=api_key)


def get_model() -> str:
    return os.getenv(
        "OPENAI_MODEL",
        "gpt-5-mini",
    )


def ask_model(
    system_prompt: str,
    user_prompt: str,
) -> str:
    client = get_client()

    response = client.responses.create(
        model=get_model(),
        instructions=system_prompt,
        input=user_prompt,
    )

    return response.output_text