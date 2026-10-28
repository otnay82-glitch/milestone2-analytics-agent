from src.query_service import run_safe_query


tests = [
    (
        "Valid analytics query",
        """
        SELECT
            carrier_id,
            SUM(shipment_count) AS total_shipments
        FROM gold.carrier_daily
        WHERE metric_date >= '2026-08-01'
          AND metric_date < '2026-09-01'
        GROUP BY carrier_id
        ORDER BY total_shipments DESC
        """,
        True,
    ),
    (
        "Unauthorized table",
        """
        SELECT *
        FROM information_schema.tables
        """,
        False,
    ),
    (
        "Unauthorized column",
        """
        SELECT carrier_id, password
        FROM gold.carrier_daily
        """,
        False,
    ),
    (
        "DELETE attempt",
        """
        DELETE FROM gold.carrier_daily
        """,
        False,
    ),
]


for name, sql, expected_success in tests:
    result = run_safe_query(sql)

    status = (
        "PASS"
        if result.success == expected_success
        else "FAIL"
    )

    print(
        f"{status:4} | "
        f"{name:24} | "
        f"success={result.success} | "
        f"error={result.error}"
    )

    if result.success:
        for row in result.rows:
            print(f"       {row}")