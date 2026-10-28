import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp


ALLOWED_COLUMNS = {
    "gold.shipment_fact": {
        "shipment_id",
        "order_date",
        "carrier_id",
        "origin_hub",
        "destination_city",
        "service_level",
        "promised_delivery_at_utc",
        "delivered_at_utc",
        "delivery_status",
        "shipping_fee_idr",
        "refund_amount_idr",
        "exception_note",
    },
    "gold.carrier_daily": {
        "metric_date",
        "carrier_id",
        "shipment_count",
        "delivered_count",
        "on_time_delivered_count",
        "late_delivered_count",
        "in_transit_count",
        "shipping_fee_idr",
        "refund_amount_idr",
    },
    "gold.city_daily": {
        "metric_date",
        "destination_city",
        "shipment_count",
        "delivered_count",
        "on_time_delivered_count",
        "late_delivered_count",
        "in_transit_count",
        "shipping_fee_idr",
        "refund_amount_idr",
    },
}


ALLOWED_TABLES = set(ALLOWED_COLUMNS.keys())


ALLOWED_FUNCTIONS = {
    "COUNT",
    "SUM",
    "AVG",
    "MIN",
    "MAX",
    "NULLIF",
    "DATE_TRUNC",
    "ROUND",
    "COALESCE",
}


FORBIDDEN_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "MERGE",
    "CALL",
    "EXEC",
    "EXECUTE",
}


@dataclass
class SQLValidationResult:
    allowed: bool
    reason: str


def normalize_sql(sql: str) -> str:
    sql = sql.strip()
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"\s+", " ", sql)
    return sql.strip()


def validate_sql(sql: str) -> SQLValidationResult:
    if not isinstance(sql, str) or not sql.strip():
        return SQLValidationResult(
            False,
            "SQL kosong",
        )

    normalized = normalize_sql(sql)

    # Exactly one statement.
    try:
        statements = sqlglot.parse(
            normalized,
            read="postgres",
        )
    except Exception as exc:
        return SQLValidationResult(
            False,
            f"SQL tidak dapat diparse: {exc}",
        )

    if len(statements) != 1:
        return SQLValidationResult(
            False,
            "Multiple SQL statements tidak diizinkan",
        )

    tree = statements[0]

    # SELECT only.
    if not isinstance(tree, exp.Select):
        return SQLValidationResult(
            False,
            "Hanya SELECT yang diizinkan",
        )

    # Explicit forbidden operations.
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(
            rf"\b{re.escape(keyword)}\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            return SQLValidationResult(
                False,
                f"SQL keyword terlarang: {keyword}",
            )

    # Collect physical table references.
    tables = tree.find_all(exp.Table)

    if not tables:
        return SQLValidationResult(
            False,
            "Tidak ditemukan tabel pada query",
        )

    allowed_tables_lower = {
        table_name.lower()
        for table_name in ALLOWED_TABLES
    }

    table_map = {}

    for table in tables:
        catalog = table.catalog
        db = table.db
        name = table.name

        if catalog:
            full_name = f"{catalog}.{db}.{name}"
        elif db:
            full_name = f"{db}.{name}"
        else:
            full_name = name

        full_name = full_name.lower()

        if full_name not in allowed_tables_lower:
            return SQLValidationResult(
                False,
                f"Tabel tidak diizinkan: {full_name}",
            )

        alias = table.alias_or_name.lower()
        table_map[alias] = full_name

    # ---------------------------------------------------------
    # Function validation
    # ---------------------------------------------------------
    #
    # Do NOT use exp.Func as a generic function detector.
    # SQLGlot's Func hierarchy also contains expressions such
    # as AND and CASE.
    #
    # Anonymous functions are the important case here because
    # arbitrary PostgreSQL functions such as pg_sleep() can be
    # represented as Anonymous.
    #
    for function in tree.find_all(exp.Anonymous):
        function_name = function.name.upper()

        if function_name not in {
            name.upper()
            for name in ALLOWED_FUNCTIONS
        }:
            return SQLValidationResult(
                False,
                f"Fungsi SQL tidak diizinkan: {function_name}",
            )

    # ---------------------------------------------------------
    # Validate known aggregate functions explicitly.
    # ---------------------------------------------------------

    aggregate_function_names = {
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX",
    }

    for function in tree.find_all(exp.AggFunc):
        function_name = function.sql_name().upper()

        if function_name not in aggregate_function_names:
            return SQLValidationResult(
                False,
                f"Fungsi aggregate tidak diizinkan: {function_name}",
            )

    # ---------------------------------------------------------
    # Validate scalar functions that are explicitly supported.
    # ---------------------------------------------------------

    scalar_function_names = {
        "NULLIF",
        "ROUND",
        "COALESCE",
    }

    scalar_function_classes = (
        exp.Nullif,
        exp.Round,
        exp.Coalesce,
    )

    for function_class in scalar_function_classes:
        for function in tree.find_all(function_class):
            function_name = function.sql_name().upper()

            if function_name not in scalar_function_names:
                return SQLValidationResult(
                    False,
                    f"Fungsi SQL tidak diizinkan: {function_name}",
                )

    # PostgreSQL DATE_TRUNC is represented by SQLGlot as
    # TimestampTrunc in the PostgreSQL dialect.
    for function in tree.find_all(exp.TimestampTrunc):
        function_name = "DATE_TRUNC"

        if function_name not in ALLOWED_FUNCTIONS:
            return SQLValidationResult(
                False,
                f"Fungsi SQL tidak diizinkan: {function_name}",
            )

    # Collect aliases defined in SELECT.
    select_aliases = {
        alias.alias.lower()
        for alias in tree.find_all(exp.Alias)
        if alias.alias
    }

    # Validate every referenced column.
    for column in tree.find_all(exp.Column):
        column_name = column.name.lower()
        table_name = (
            column.table.lower()
            if column.table
            else None
        )

        # SELECT aliases such as:
        # DATE_TRUNC(...) AS week_start
        # ORDER BY week_start
        if (
            not table_name
            and column_name in select_aliases
        ):
            continue

        if table_name:
            if table_name not in table_map:
                return SQLValidationResult(
                    False,
                    f"Alias/tabel tidak diizinkan: {table_name}",
                )

            physical_table = table_map[table_name]

            allowed_columns = {
                col.lower()
                for col in ALLOWED_COLUMNS[physical_table]
            }

            if column_name not in allowed_columns:
                return SQLValidationResult(
                    False,
                    f"Kolom tidak diizinkan: "
                    f"{table_name}.{column_name}",
                )

        else:
            # Unqualified column.
            matching_tables = [
                physical_table
                for physical_table in table_map.values()
                if column_name in {
                    col.lower()
                    for col in ALLOWED_COLUMNS[physical_table]
                }
            ]

            if not matching_tables:
                return SQLValidationResult(
                    False,
                    f"Kolom tidak diizinkan: {column_name}",
                )

    return SQLValidationResult(
        True,
        "SQL valid",
    )