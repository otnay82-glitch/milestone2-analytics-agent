from src.query_service import run_safe_query


sql = """
SELECT
    shipment_id,
    exception_note
FROM gold.shipment_fact
WHERE exception_note IS NOT NULL
LIMIT 20
"""

result = run_safe_query(sql)

print("SUCCESS:", result.success)
print("ERROR:", result.error)
print("ROWS:", len(result.rows))

for row in result.rows:
    print("-" * 70)
    print("shipment_id:", row["shipment_id"])
    print("exception_note:", row["exception_note"])