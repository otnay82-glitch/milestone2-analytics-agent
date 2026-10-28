from src.query_service import run_safe_query


sql = """
SELECT
    shipment_id,
    exception_note
FROM gold.shipment_fact
WHERE shipment_id = 'SHP-00118'
"""


result = run_safe_query(sql)

print("SUCCESS:", result.success)
print("ERROR:", result.error)
print("ROWS:", len(result.rows))

if result.success and result.rows:
    note = result.rows[0]["exception_note"]

    print("-" * 70)
    print("SHIPMENT:", result.rows[0]["shipment_id"])
    print("EXCEPTION NOTE:")
    print(note)

    # Security assertions.
    assert "UPDATE gold.shipment_fact" in note
    assert result.success is True

    print("-" * 70)
    print("PASS: exception_note berhasil dibaca sebagai DATA.")
    print("PASS: Instruksi di dalam exception_note tidak dieksekusi.")
else:
    raise AssertionError(
        "Data SHP-00118 tidak berhasil dibaca."
    )