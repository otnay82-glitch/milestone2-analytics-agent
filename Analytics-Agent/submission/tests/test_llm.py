from src.llm_client import ask_model


answer = ask_model(
    system_prompt=(
        "Jawab singkat dalam Bahasa Indonesia. "
        "Ini hanya smoke test."
    ),
    user_prompt="Sebutkan satu kata yang menggambarkan analitik data.",
)

print("MODEL RESPONSE:")
print(answer)