from src.planner import AnalyticsPlan
from src.sql_builder import build_sql
from src.sql_guard import validate_sql


def test_shipments_per_carrier_sql_is_safe():
    plan = AnalyticsPlan(
        intent="shipments_per_carrier",
        table="gold.carrier_daily",
        metric="SUM(shipment_count)",
        filters={
            "metric_date": {
                "gte": "2026-08-01",
                "lt": "2026-09-01",
            }
        },
        group_by=["carrier_id"],
        order_by="shipment_count DESC",
    )

    sql = build_sql(plan)

    assert "SELECT" in sql.upper()
    assert "gold.carrier_daily" in sql
    assert "SUM(shipment_count)" in sql
    assert "GROUP BY carrier_id" in sql
    assert "2026-08-01" in sql
    assert "2026-09-01" in sql

    result = validate_sql(sql)

    assert result.allowed is True, result.reason