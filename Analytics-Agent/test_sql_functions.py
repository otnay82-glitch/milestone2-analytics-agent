from src.sql_guard import validate_sql


tests = [
    (
        "COUNT allowed",
        """
        SELECT carrier_id, COUNT(*) AS total
        FROM gold.carrier_daily
        GROUP BY carrier_id
        """,
        True,
    ),
    (
        "SUM allowed",
        """
        SELECT SUM(shipping_fee_idr) AS total_fee
        FROM gold.carrier_daily
        """,
        True,
    ),
    (
        "DATE_TRUNC allowed",
        """
        SELECT DATE_TRUNC('week', metric_date) AS week_start,
               SUM(shipment_count) AS shipments
        FROM gold.city_daily
        GROUP BY week_start
        """,
        True,
    ),
    (
        "ROUND allowed",
        """
        SELECT ROUND(
            SUM(refund_amount_idr) /
            NULLIF(SUM(shipping_fee_idr), 0) * 100,
            2
        ) AS refund_rate
        FROM gold.shipment_fact
        """,
        True,
    ),
    (
        "PG_SLEEP blocked",
        """
        SELECT pg_sleep(5)
        FROM gold.shipment_fact
        """,
        False,
    ),
]


for name, sql, expected in tests:
    result = validate_sql(sql)

    if result.allowed == expected:
        print(f"PASS | {name} | {result.reason}")
    else:
        print(
            f"FAIL | {name} | "
            f"expected={expected}, "
            f"actual={result.allowed}, "
            f"reason={result.reason}"
        )