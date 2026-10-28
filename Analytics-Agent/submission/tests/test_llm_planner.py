from src.llm_planner import plan_question


plan = plan_question(
    user_message=(
        "Berapa jumlah shipment per carrier "
        "pada Agustus 2026?"
    ),
    conversation_history=[],
)

print("PLANNER RESULT")
print("intent:", plan.intent)
print("table:", plan.table)
print("metric:", plan.metric)
print("filters:", plan.filters)
print("group_by:", plan.group_by)
print("order_by:", plan.order_by)
print("limit:", plan.limit)
print("needs_clarification:", plan.needs_clarification)
print("clarification_question:", plan.clarification_question)