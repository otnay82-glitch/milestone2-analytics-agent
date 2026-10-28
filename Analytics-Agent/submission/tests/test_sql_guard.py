from src.sql_guard import validate_sql


tests = [
    (
        "Basic SELECT",
        """
        SELECT carrier_id, shipment_count
        FROM gold.carrier_daily
        """,
        True,
    ),
    (
        "Alias + aggregate",
        """
        SELECT c.carrier_id, SUM(c.shipment_count) AS total_shipments
        FROM gold.carrier_daily AS c
        WHERE c.metric_date >= '2026-08-01'
          AND c.metric_date < '2026-09-01'
        GROUP BY c.carrier_id
        """,
        True,
    ),
    (
        "COUNT shipment_fact",
        """
        SELECT COUNT(*) AS total_shipments
        FROM gold.shipment_fact
        WHERE order_date >= '2026-08-01'
          AND order_date < '2026-09-01'
        """,
        True,
    ),
    (
        "DATE_TRUNC weekly",
        """
        SELECT
            DATE_TRUNC('week', c.metric_date) AS week_start,
            SUM(c.shipment_count) AS shipments
        FROM gold.city_daily AS c
        WHERE c.destination_city = 'Bandung'
          AND c.metric_date >= '2026-08-01'
          AND c.metric_date < '2026-09-01'
        GROUP BY DATE_TRUNC('week', c.metric_date)
        ORDER BY week_start
        """,
        True,
    ),
    (
        "CASE expression",
        """
        SELECT
            carrier_id,
            SUM(
                CASE
                    WHEN delivered_count > 0
                    THEN on_time_delivered_count
                    ELSE 0
                END
            ) AS on_time
        FROM gold.carrier_daily
        GROUP BY carrier_id
        """,
        True,
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
        "Unauthorized table",
        """
        SELECT *
        FROM information_schema.tables
        """,
        False,
    ),
    (
        "INSERT",
        """
        INSERT INTO gold.carrier_daily
        VALUES ('2026-10-01', 'C01', 1, 1, 1, 0, 0, 1000, 0)
        """,
        False,
    ),
    (
        "Multiple statements",
        """
        SELECT carrier_id
        FROM gold.carrier_daily;
        DELETE FROM gold.carrier_daily;
        """,
        False,
    ),
]


for name, sql, expected in tests:
    result = validate_sql(sql)

    status = "PASS" if result.allowed == expected else "FAIL"

    print(
        f"{status:4} | "
        f"{name:24} | "
        f"allowed={result.allowed} | "
        f"{result.reason}"
    )