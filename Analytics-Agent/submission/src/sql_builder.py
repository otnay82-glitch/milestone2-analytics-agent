from datetime import date, timedelta

from src.planner import AnalyticsPlan


def _get_date_range(
    date_filter: dict,
) -> tuple[str, str]:
    """
    Convert planner date filters into a half-open date range:
    [start_date, end_date)
    """

    if "between" in date_filter:
        start_date = date_filter["between"][0]
        inclusive_end = date.fromisoformat(
            date_filter["between"][1]
        )
        end_date = (
            inclusive_end + timedelta(days=1)
        ).isoformat()

    elif "from" in date_filter:
        start_date = date_filter["from"]

        if "to" in date_filter:
            inclusive_end = date.fromisoformat(
                date_filter["to"]
            )
            end_date = (
                inclusive_end + timedelta(days=1)
            ).isoformat()

        elif "lt" in date_filter:
            end_date = date_filter["lt"]

        elif "lte" in date_filter:
            inclusive_end = date.fromisoformat(
                date_filter["lte"]
            )
            end_date = (
                inclusive_end + timedelta(days=1)
            ).isoformat()

        else:
            raise ValueError(
                "Filter tanggal tidak memiliki end date"
            )

    elif "gte" in date_filter:
        start_date = date_filter["gte"]

        if "lt" in date_filter:
            end_date = date_filter["lt"]

        elif "lte" in date_filter:
            inclusive_end = date.fromisoformat(
                date_filter["lte"]
            )
            end_date = (
                inclusive_end + timedelta(days=1)
            ).isoformat()

        else:
            raise ValueError(
                "Filter tanggal tidak memiliki end date"
            )

    else:
        raise ValueError(
            "Filter tanggal tidak memiliki start date"
        )

    return start_date, end_date


def build_shipments_per_carrier_sql(
    plan: AnalyticsPlan,
) -> str:
    """
    Build SQL for shipments per carrier.
    """

    start_date, end_date = _get_date_range(
        plan.filters["metric_date"]
    )

    return f"""
        SELECT
            carrier_id,
            SUM(shipment_count) AS total_shipments
        FROM gold.carrier_daily
        WHERE metric_date >= DATE '{start_date}'
          AND metric_date < DATE '{end_date}'
        GROUP BY carrier_id
        ORDER BY total_shipments DESC
    """.strip()


def build_best_on_time_carrier_sql(
    plan: AnalyticsPlan,
) -> str:
    """
    Build SQL for the carrier with the highest
    on-time delivery rate.

    Only carriers with at least 20 delivered shipments
    are eligible.
    """

    start_date, end_date = _get_date_range(
        plan.filters["metric_date"]
    )

    delivered_filter = plan.filters.get(
        "delivered_count",
        {},
    )

    min_delivered = delivered_filter.get(
        "gte",
        20,
    )

    if not isinstance(min_delivered, int):
        min_delivered = int(min_delivered)

    if min_delivered < 1:
        raise ValueError(
            "Minimum delivered_count harus lebih besar dari 0"
        )

    return f"""
        SELECT
            carrier_id,
            SUM(on_time_delivered_count)
                AS on_time_delivered,
            SUM(delivered_count)
                AS delivered,
            ROUND(
                SUM(on_time_delivered_count) * 100.0
                / NULLIF(SUM(delivered_count), 0),
                2
            ) AS on_time_rate_pct
        FROM gold.carrier_daily
        WHERE metric_date >= DATE '{start_date}'
          AND metric_date < DATE '{end_date}'
        GROUP BY carrier_id
        HAVING SUM(delivered_count) >= {min_delivered}
        ORDER BY on_time_rate_pct DESC
        LIMIT 1
    """.strip()


def build_express_refund_rate_sql(
    plan: AnalyticsPlan,
) -> str:
    """
    Build SQL for Express refund rate.

    Refund rate:
        SUM(refund_amount_idr)
        /
        SUM(shipping_fee_idr)
    """

    start_date, end_date = _get_date_range(
        plan.filters["order_date"]
    )

    service_level = plan.filters.get(
        "service_level"
    )

    if service_level != "express":
        raise ValueError(
            "SQL Builder ini hanya mendukung "
            "service_level = express"
        )

    return f"""
        SELECT
            SUM(refund_amount_idr)
                AS refund_amount_idr,
            SUM(shipping_fee_idr)
                AS shipping_fee_idr,
            ROUND(
                SUM(refund_amount_idr) * 100.0
                / NULLIF(SUM(shipping_fee_idr), 0),
                2
            ) AS refund_rate_pct
        FROM gold.shipment_fact
        WHERE service_level = 'express'
          AND order_date >= DATE '{start_date}'
          AND order_date < DATE '{end_date}'
    """.strip()


def build_weekly_comparison_sql(
    plan: AnalyticsPlan,
) -> str:
    """
    Build SQL for comparing the requested 7-day period
    with the immediately preceding 7-day period.

    The current implementation supports the carrier context
    established by the previous question.
    """

    if plan.table != "gold.carrier_daily":
        raise ValueError(
            "Weekly comparison saat ini hanya mendukung "
            "gold.carrier_daily"
        )

    if plan.group_by != ["carrier_id"]:
        raise ValueError(
            "Weekly comparison saat ini harus "
            "group_by carrier_id"
        )

    date_filter = plan.filters.get("metric_date")

    if not isinstance(date_filter, dict):
        raise ValueError(
            "Weekly comparison membutuhkan "
            "filter metric_date"
        )

    current_start, current_end_inclusive = (
        _get_date_range(date_filter)
    )

    current_start_date = date.fromisoformat(
        current_start
    )

    current_end_exclusive = date.fromisoformat(
        current_end_inclusive
    )

    current_days = (
        current_end_exclusive - current_start_date
    ).days

    if current_days != 7:
        raise ValueError(
            "Weekly comparison harus menggunakan "
            "periode tepat 7 hari"
        )

    previous_start = (
        current_start_date - timedelta(days=7)
    )

    previous_end = current_start_date

    return f"""
        SELECT
            carrier_id,

            SUM(
                CASE
                    WHEN metric_date >= DATE '{previous_start.isoformat()}'
                     AND metric_date < DATE '{previous_end.isoformat()}'
                    THEN shipment_count
                    ELSE 0
                END
            ) AS previous_week_shipments,

            SUM(
                CASE
                    WHEN metric_date >= DATE '{current_start_date.isoformat()}'
                     AND metric_date < DATE '{current_end_exclusive.isoformat()}'
                    THEN shipment_count
                    ELSE 0
                END
            ) AS current_week_shipments,

            SUM(
                CASE
                    WHEN metric_date >= DATE '{current_start_date.isoformat()}'
                     AND metric_date < DATE '{current_end_exclusive.isoformat()}'
                    THEN shipment_count
                    ELSE 0
                END
            )
            -
            SUM(
                CASE
                    WHEN metric_date >= DATE '{previous_start.isoformat()}'
                     AND metric_date < DATE '{previous_end.isoformat()}'
                    THEN shipment_count
                    ELSE 0
                END
            ) AS change_shipments

        FROM gold.carrier_daily

        WHERE metric_date >= DATE '{previous_start.isoformat()}'
          AND metric_date < DATE '{current_end_exclusive.isoformat()}'

        GROUP BY carrier_id
        ORDER BY carrier_id
    """.strip()


def build_sql(
    plan: AnalyticsPlan,
) -> str:
    """
    Convert a validated analytics plan into SQL.

    The caller must run Plan Guard before calling this function.
    """

    if plan.intent == "shipments_per_carrier":
        return build_shipments_per_carrier_sql(plan)

    if plan.intent == "best_on_time_carrier":
        return build_best_on_time_carrier_sql(plan)

    if plan.intent == "express_refund_rate":
        return build_express_refund_rate_sql(plan)

    if plan.intent == "weekly_comparison":
        return build_weekly_comparison_sql(plan)

    raise ValueError(
        f"Intent belum didukung SQL Builder: {plan.intent}"
    )