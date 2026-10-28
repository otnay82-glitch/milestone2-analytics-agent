from src.agent import run_agent


history = []

# Turn 1
question_1 = (
    "Berapa jumlah shipment Bandung pada minggu "
    "10 Agustus 2026?"
)

result_1 = run_agent(
    question_1,
    history,
)

print("=" * 70)
print("TURN 1")
print("QUESTION:", question_1)
print("OUTCOME:", result_1.outcome)
print("ANSWER:", result_1.answer)
print("DATA BASIS:", result_1.data_basis)


# Simulate conversation history.
history.append({
    "role": "user",
    "content": question_1,
})

history.append({
    "role": "assistant",
    "content": result_1.answer,
})


# Turn 2 — follow-up
question_2 = "Bagaimana dibanding minggu sebelumnya?"

result_2 = run_agent(
    question_2,
    history,
)

print("=" * 70)
print("TURN 2")
print("QUESTION:", question_2)
print("OUTCOME:", result_2.outcome)
print("ANSWER:", result_2.answer)
print("DATA BASIS:", result_2.data_basis)