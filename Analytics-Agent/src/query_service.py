from dataclasses import dataclass

from src.db import execute_read_only
from src.sql_guard import validate_sql


@dataclass
class QueryResult:
    success: bool
    rows: list[dict]
    error: str


def run_safe_query(sql: str) -> QueryResult:
    """
    Validate SQL first, then execute it against Neon.

    No SQL should reach the database without passing
    the SQL Guard.
    """

    validation = validate_sql(sql)

    if not validation.allowed:
        return QueryResult(
            success=False,
            rows=[],
            error=validation.reason,
        )

    try:
        rows = execute_read_only(sql)

        return QueryResult(
            success=True,
            rows=rows,
            error="",
        )

    except Exception as exc:
        return QueryResult(
            success=False,
            rows=[],
            error=f"Query execution failed: {exc}",
        )