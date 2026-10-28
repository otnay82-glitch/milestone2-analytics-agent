import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

conn = psycopg.connect(os.environ["GOLD_DATABASE_URL"])

with conn.cursor() as cur:
    cur.execute("""
        SELECT
            SUM(refund_amount_idr) AS total_refund_idr,
            SUM(shipping_fee_idr) AS total_shipping_fee_idr,
            ROUND(
                SUM(refund_amount_idr)
                / NULLIF(SUM(shipping_fee_idr), 0) * 100,
                2
            ) AS refund_rate_pct
        FROM gold.shipment_fact
        WHERE service_level = 'express'
          AND order_date BETWEEN DATE '2026-09-01'
                             AND DATE '2026-09-20'
    """)

    row = cur.fetchone()

    print(f"Express refund       : Rp {row[0]:,.2f}")
    print(f"Express shipping fee : Rp {row[1]:,.2f}")
    print(f"Refund rate          : {row[2]:.2f}%")

conn.close()