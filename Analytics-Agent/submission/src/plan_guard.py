from src.planner import AnalyticsPlan, SUPPORTED_INTENTS
from src.sql_guard import ALLOWED_COLUMNS, ALLOWED_TABLES


MAX_PLAN_LIMIT = 100


def validate_plan(plan: AnalyticsPlan) -> tuple[bool, str]:
    if plan.intent not in SUPPORTED_INTENTS:
        return False, "Intent tidak diizinkan"

    if plan.needs_clarification:
        return True, "Plan membutuhkan klarifikasi"

    if plan.table not in ALLOWED_TABLES:
        return False, f"Tabel tidak diizinkan: {plan.table}"

    allowed_columns = {
        column.lower()
        for column in ALLOWED_COLUMNS[plan.table]
    }

    for column in plan.group_by:
        if column.lower() not in allowed_columns:
            return False, f"Group-by tidak diizinkan: {column}"

    for column in plan.filters:
        if column.lower() not in allowed_columns:
            return False, f"Filter tidak diizinkan: {column}"

    if plan.limit < 1 or plan.limit > MAX_PLAN_LIMIT:
        return False, "Limit plan tidak valid"

    return True, "Plan valid"