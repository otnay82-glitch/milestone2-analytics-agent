import os
import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["GOLD_DATABASE_URL"]
CSV_PATH = "data/city_daily.csv"

df = pd.read_csv(CSV_PATH)

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        rows = [
            (
                row.metric_date,
                row.destination_city,
                row.shipment_count,
                row.delivered_count,
                row.on_time_delivered_count,
                row.late_delivered_count,
                row.in_transit_count,
                row.shipping_fee_idr,
                row.refund_amount_idr,
            )
            for row in df.itertuples(index=False)
        ]

        cur.executemany(
            """
            INSERT INTO gold.city_daily (
                metric_date,
                destination_city,
                shipment_count,
                delivered_count,
                on_time_delivered_count,
                late_delivered_count,
                in_transit_count,
                shipping_fee_idr,
                refund_amount_idr
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )

print(f"Imported {len(rows)} rows into gold.city_daily")