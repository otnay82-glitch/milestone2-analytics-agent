from src.agent import run_agent


tests = [
    "Berapa jumlah shipment per carrier pada Agustus 2026?",
    "Carrier mana dengan on-time rate tertinggi pada Agustus 2026?",
    "Berapa refund rate untuk Express pada September 2026?",
    "Bagaimana cuaca hari ini?",
]


for question in tests:
    print("=" * 70)
    print("QUESTION:", question)

    result = run_agent(
        question,
        conversation_history=[],
    )

    print("OUTCOME:", result.outcome)
    print("ANSWER:", result.answer)
    print("DATA BASIS:", result.data_basis)