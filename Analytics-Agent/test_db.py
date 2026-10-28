from src.db import execute_read_only


sql = """
SELECT
    carrier_id,
    SUM(shipment_count) AS total_shipments
FROM gold.carrier_daily
WHERE metric_date >= '2026-08-01'
  AND metric_date < '2026-09-01'
GROUP BY carrier_id
ORDER BY total_shipments DESC
"""


rows = execute_read_only(sql)

print("ROWS:", len(rows))

for row in rows:
    print(row)