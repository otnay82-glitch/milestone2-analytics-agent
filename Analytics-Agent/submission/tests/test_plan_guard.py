from src.plan_guard import validate_plan
from src.planner import AnalyticsPlan


tests = [
    (
        "Valid carrier plan",
        AnalyticsPlan(
            intent="shipments_per_carrier",
            table="gold.carrier_daily",
            metric="SUM(shipment_count)",
            filters={
                "metric_date": {
                    "gte": "2026-08-01",
                    "lte": "2026-08-31",
                }
            },
            group_by=["carrier_id"],
            order_by="shipment_count DESC",
            limit=100,
        ),
        True,
    ),
    (
        "Unauthorized table",
        AnalyticsPlan(
            intent="shipments_per_carrier",
            table="gold.users",
            metric="COUNT(*)",
            filters={},
            group_by=[],
            limit=100,
        ),
        False,
    ),
    (
        "Unauthorized group by",
        AnalyticsPlan(
            intent="shipments_per_carrier",
            table="gold.carrier_daily",
            metric="SUM(shipment_count)",
            filters={},
            group_by=["password"],
            limit=100,
        ),
        False,
    ),
    (
        "Unauthorized filter",
        AnalyticsPlan(
            intent="shipments_per_carrier",
            table="gold.carrier_daily",
            metric="SUM(shipment_count)",
            filters={"password": "secret"},
            group_by=["carrier_id"],
            limit=100,
        ),
        False,
    ),
    (
        "Limit too high",
        AnalyticsPlan(
            intent="shipments_per_carrier",
            table="gold.carrier_daily",
            metric="SUM(shipment_count)",
            filters={},
            group_by=["carrier_id"],
            limit=1000,
        ),
        False,
    ),
]


for name, plan, expected in tests:
    allowed, reason = validate_plan(plan)

    if allowed == expected:
        print(
            f"PASS | {name:<24} | "
            f"allowed={allowed} | {reason}"
        )
    else:
        print(
            f"FAIL | {name:<24} | "
            f"expected={expected}, "
            f"actual={allowed} | {reason}"
        )