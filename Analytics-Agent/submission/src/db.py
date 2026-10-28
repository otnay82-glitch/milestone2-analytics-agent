import os
from decimal import Decimal

import psycopg
from dotenv import load_dotenv


load_dotenv()


MAX_ROWS = 500
STATEMENT_TIMEOUT_MS = 5000


def get_database_url() -> str:
    database_url = os.getenv("GOLD_DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "GOLD_DATABASE_URL belum dikonfigurasi"
        )

    return database_url


def execute_read_only(sql: str) -> list[dict]:
    """
    Execute an already-validated SELECT query against Neon Gold.

    SQL validation MUST happen before this function is called.
    """

    database_url = get_database_url()

    with psycopg.connect(database_url) as conn:
        # Defense in depth:
        # explicitly make the current transaction read-only.
        conn.execute("SET TRANSACTION READ ONLY")

        # Apply query execution timeout after connection.
        conn.execute(
            f"SET LOCAL statement_timeout = "
            f"{STATEMENT_TIMEOUT_MS}"
        )

        with conn.cursor() as cur:
            cur.execute(sql)

            rows = cur.fetchmany(MAX_ROWS)

            columns = [
                description.name
                for description in cur.description
            ]

            return [
                {
                    column: normalize_value(value)
                    for column, value in zip(columns, row)
                }
                for row in rows
            ]


def normalize_value(value):
    """Convert PostgreSQL-specific numeric values to JSON-friendly values."""

    if isinstance(value, Decimal):
        return float(value)

    return value