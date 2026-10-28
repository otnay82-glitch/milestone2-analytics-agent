from dataclasses import dataclass
import re
from datetime import date, timedelta

from src.query_service import run_safe_query
from src.scope_guard import check_scope
from src.llm_planner import plan_question
from src.plan_guard import validate_plan
from src.sql_builder import build_sql as build_plan_sql


@dataclass
class AgentResult:
    answer: str
    data_basis: str
    outcome: str


def format_idr(value: float) -> str:
    return f"Rp{value:,.0f}".replace(",", ".")


def detect_intent(user_message: str) -> str | None:
    text = user_message.lower()

    if (
        "dibanding minggu sebelumnya" in text
        or "bandingkan dengan minggu sebelumnya" in text
        or "vs minggu sebelumnya" in text
    ):
        return "weekly_comparison"

    if (
        "shipment" in text
        and "bandung" in text
        and "minggu" in text
    ):
        return "weekly_city_shipments"

    if (
        "shipment per carrier" in text
        or (
            "jumlah shipment" in text
            and "carrier" in text
        )
    ):
        return "shipments_per_carrier"

    if (
        "on-time" in text
        or "ontime" in text
        or "on time" in text
    ) and "carrier" in text:
        return "best_on_time_carrier"

    if (
        "refund rate" in text
        and "express" in text
    ):
        return "express_refund_rate"

    return None


def extract_month_range(text: str) -> tuple[str, str] | None:
    text = text.lower()

    months = {
        "januari": 1,
        "februari": 2,
        "maret": 3,
        "april": 4,
        "mei": 5,
        "juni": 6,
        "juli": 7,
        "agustus": 8,
        "september": 9,
        "oktober": 10,
        "november": 11,
        "desember": 12,
        "january": 1,
        "february": 2,
        "march": 3,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "october": 10,
        "november": 11,
        "december": 12,
    }

    match = re.search(
        r"(januari|februari|maret|april|mei|juni|"
        r"juli|agustus|september|oktober|november|desember|"
        r"january|february|march|may|june|july|august|"
        r"october|november|december)\s+(\d{4})",
        text,
    )

    if not match:
        return None

    month_name = match.group(1)
    year = int(match.group(2))
    month = months[month_name]

    if month == 12:
        next_month = f"{year + 1:04d}-01-01"
    else:
        next_month = f"{year:04d}-{month + 1:02d}-01"

    start = f"{year:04d}-{month:02d}-01"

    return start, next_month


def extract_week(text: str) -> tuple[str, str] | None:
    text = text.lower()

    months = {
        "januari": 1,
        "februari": 2,
        "maret": 3,
        "april": 4,
        "mei": 5,
        "juni": 6,
        "juli": 7,
        "agustus": 8,
        "september": 9,
        "oktober": 10,
        "november": 11,
        "desember": 12,
    }

    match = re.search(
        r"minggu\s+(\d{1,2})\s+"
        r"(januari|februari|maret|april|mei|juni|"
        r"juli|agustus|september|oktober|november|desember)"
        r"\s+(\d{4})",
        text,
    )

    if not match:
        return None

    day = int(match.group(1))
    month = months[match.group(2)]
    year = int(match.group(3))

    reference_date = date(year, month, day)

    monday = reference_date - timedelta(
        days=reference_date.weekday()
    )
    next_monday = monday + timedelta(days=7)

    return (
        monday.isoformat(),
        next_monday.isoformat(),
    )


def extract_city(text: str) -> str | None:
    match = re.search(
        r"\b(bandung|jakarta|surabaya|depok|bogor)\b",
        text.lower(),
    )

    if not match:
        return None

    return match.group(1).title()


def get_last_user_message(
    conversation_history: list[dict],
) -> str | None:
    for message in reversed(conversation_history):
        if message.get("role") == "user":
            return message.get("content")

    return None


def build_sql(
    intent: str,
    date_range: tuple[str, str],
    city: str | None = None,
) -> str:

    start_date, end_date = date_range

    if intent == "shipments_per_carrier":
        return f"""
        SELECT
            carrier_id,
            SUM(shipment_count) AS total_shipments
        FROM gold.carrier_daily
        WHERE metric_date >= '{start_date}'
          AND metric_date < '{end_date}'
        GROUP BY carrier_id
        ORDER BY total_shipments DESC
        """

    if intent == "best_on_time_carrier":
        return f"""
        SELECT
            carrier_id,
            SUM(delivered_count) AS delivered_count,
            SUM(on_time_delivered_count)
                AS on_time_delivered_count,
            SUM(on_time_delivered_count)::numeric
                / NULLIF(SUM(delivered_count), 0)
                AS on_time_rate
        FROM gold.carrier_daily
        WHERE metric_date >= '{start_date}'
          AND metric_date < '{end_date}'
        GROUP BY carrier_id
        HAVING SUM(delivered_count) >= 20
        ORDER BY on_time_rate DESC
        LIMIT 1
        """

    if intent == "express_refund_rate":
        return f"""
        SELECT
            SUM(refund_amount_idr) AS refund_amount_idr,
            SUM(shipping_fee_idr) AS shipping_fee_idr,
            SUM(refund_amount_idr)
                / NULLIF(SUM(shipping_fee_idr), 0)
                AS refund_rate
        FROM gold.shipment_fact
        WHERE service_level = 'express'
          AND order_date >= '{start_date}'
          AND order_date < '{end_date}'
        """

    if intent == "weekly_city_shipments":
        if not city:
            raise ValueError("City tidak tersedia")

        return f"""
        SELECT
            SUM(shipment_count) AS total_shipments
        FROM gold.city_daily
        WHERE destination_city = '{city}'
          AND metric_date >= '{start_date}'
          AND metric_date < '{end_date}'
        """

    if intent == "weekly_comparison":
        if not city:
            raise ValueError("City tidak tersedia")

        previous_start = (
            date.fromisoformat(start_date)
            - timedelta(days=7)
        ).isoformat()

        return f"""
        SELECT
            SUM(
                CASE
                    WHEN metric_date >= '{start_date}'
                     AND metric_date < '{end_date}'
                    THEN shipment_count
                    ELSE 0
                END
            ) AS current_shipments,
            SUM(
                CASE
                    WHEN metric_date >= '{previous_start}'
                     AND metric_date < '{start_date}'
                    THEN shipment_count
                    ELSE 0
                END
            ) AS previous_shipments
        FROM gold.city_daily
        WHERE destination_city = '{city}'
          AND metric_date >= '{previous_start}'
          AND metric_date < '{end_date}'
        """

    raise ValueError(f"Intent tidak dikenal: {intent}")


def run_agent(
    user_message: str,
    conversation_history: list[dict],
) -> AgentResult:

    scope = check_scope(user_message)

    if not scope.allowed:
        return AgentResult(
            answer=(
                "Maaf, permintaan tersebut berada di luar "
                "scope Analytics Agent."
            ),
            data_basis="",
            outcome="out_of_scope",
        )

    intent = detect_intent(user_message)

    if intent == "weekly_comparison":
        previous_user_message = get_last_user_message(
            conversation_history
        )

        if not previous_user_message:
            return AgentResult(
                answer=(
                    "Saya memerlukan pertanyaan sebelumnya "
                    "untuk memahami perbandingan minggu."
                ),
                data_basis="",
                outcome="clarification",
            )

        previous_week = extract_week(previous_user_message)
        city = extract_city(previous_user_message)

        if not previous_week or not city:
            return AgentResult(
                answer=(
                    "Saya belum dapat menentukan kota dan "
                    "periode dari pertanyaan sebelumnya."
                ),
                data_basis="",
                outcome="clarification",
            )

        date_range = previous_week

    else:
        date_range = extract_week(user_message)
        city = extract_city(user_message)

        if date_range is None:
            date_range = extract_month_range(user_message)

    if intent == "weekly_city_shipments":
        if not date_range or not city:
            return AgentResult(
                answer=(
                    "Mohon sebutkan kota dan periode minggu "
                    "secara jelas."
                ),
                data_basis="",
                outcome="clarification",
            )

    elif intent == "weekly_comparison":
        if not date_range or not city:
            return AgentResult(
                answer=(
                    "Mohon berikan konteks kota dan periode "
                    "pada pertanyaan sebelumnya."
                ),
                data_basis="",
                outcome="clarification",
            )

    elif date_range is None:
        return AgentResult(
            answer=(
                "Mohon sebutkan periode analisis secara jelas, "
                "misalnya Agustus 2026."
            ),
            data_basis="",
            outcome="clarification",
        )

    sql = build_sql(
        intent,
        date_range,
        city,
    )

    result = run_safe_query(sql)

    if not result.success:
        return AgentResult(
            answer=(
                "Data tidak dapat diperoleh karena query "
                "tidak dapat dijalankan dengan aman."
            ),
            data_basis="",
            outcome="no_data",
        )

    if not result.rows:
        return AgentResult(
            answer=(
                "Tidak ditemukan data untuk periode dan "
                "kriteria tersebut."
            ),
            data_basis="Gold dataset",
            outcome="no_data",
        )

    start_date, end_date = date_range

    if intent == "weekly_city_shipments":
        total = int(result.rows[0]["total_shipments"])

        answer = (
            f"Jumlah shipment untuk {city} pada minggu "
            f"{start_date} sampai sebelum {end_date} "
            f"adalah {total} shipment."
        )

        data_basis = (
            "gold.city_daily; "
            "shipment_count; "
            f"destination_city = {city}; "
            f"metric_date >= {start_date} dan < {end_date}"
        )

    elif intent == "weekly_comparison":
        row = result.rows[0]

        current = int(row["current_shipments"])
        previous = int(row["previous_shipments"])
        change = current - previous

        if previous == 0:
            change_text = (
                "persentase perubahan tidak dihitung "
                "karena minggu sebelumnya bernilai 0"
            )
        else:
            change_pct = (change / previous) * 100
            change_text = f"perubahan {change_pct:.2f}%"

        answer = (
            f"Untuk {city}, minggu {start_date} sampai sebelum "
            f"{end_date} memiliki {current} shipment, sedangkan "
            f"minggu sebelumnya memiliki {previous} shipment. "
            f"Perubahannya {change} shipment, {change_text}."
        )

        data_basis = (
            "gold.city_daily; shipment_count; "
            f"destination_city = {city}; "
            f"current period {start_date} sampai sebelum {end_date}; "
            "previous period = 7 hari sebelumnya"
        )

    elif intent == "shipments_per_carrier":
        parts = []

        for row in result.rows:
            parts.append(
                f"{row['carrier_id']}: "
                f"{int(row['total_shipments'])} shipment"
            )

        answer = (
            f"Jumlah shipment per carrier untuk periode "
            f"{start_date} sampai sebelum {end_date}: "
            + "; ".join(parts)
            + "."
        )

        data_basis = (
            "gold.carrier_daily; "
            "shipment_count; "
            f"metric_date >= {start_date} dan < {end_date}"
        )

    elif intent == "best_on_time_carrier":
        row = result.rows[0]

        rate = float(row["on_time_rate"]) * 100

        answer = (
            f"Carrier dengan on-time rate tertinggi adalah "
            f"{row['carrier_id']} dengan {rate:.2f}% "
            f"({int(row['on_time_delivered_count'])} on-time "
            f"dari {int(row['delivered_count'])} delivered)."
        )

        data_basis = (
            "gold.carrier_daily; "
            "on_time_delivered_count / delivered_count; "
            f"metric_date >= {start_date} dan < {end_date}; "
            "minimum 20 delivered"
        )

    elif intent == "express_refund_rate":
        row = result.rows[0]

        refund_amount = float(row["refund_amount_idr"])
        shipping_fee = float(row["shipping_fee_idr"])
        refund_rate = float(row["refund_rate"]) * 100

        answer = (
            f"Refund rate untuk service level Express adalah "
            f"{refund_rate:.2f}%, berdasarkan refund "
            f"{format_idr(refund_amount)} dibandingkan "
            f"shipping fee {format_idr(shipping_fee)}."
        )

        data_basis = (
            "gold.shipment_fact; "
            "SUM(refund_amount_idr) / SUM(shipping_fee_idr); "
            f"service_level = express; "
            f"order_date >= {start_date} dan < {end_date}"
        )

    else:
        return AgentResult(
            answer="Analisis tidak tersedia.",
            data_basis="",
            outcome="no_data",
        )

    return AgentResult(
        answer=answer,
        data_basis=data_basis,
        outcome="answered",
    )


def run_llm_agent(
    user_message: str,
    conversation_history: list[dict],
) -> AgentResult:

    scope = check_scope(user_message)

    if not scope.allowed:
        return AgentResult(
            answer=(
                "Maaf, permintaan tersebut berada di luar "
                "scope Analytics Agent."
            ),
            data_basis="",
            outcome="out_of_scope",
        )

    try:
        plan = plan_question(
            user_message=user_message,
            conversation_history=conversation_history,
        )
    except Exception:
        return AgentResult(
            answer=(
                "Saya tidak dapat memproses pertanyaan "
                "analitik tersebut saat ini."
            ),
            data_basis="",
            outcome="no_data",
        )

    if plan.needs_clarification:
        return AgentResult(
            answer=plan.clarification_question,
            data_basis="",
            outcome="clarification",
        )

    valid, reason = validate_plan(plan)

    if not valid:
        return AgentResult(
            answer=(
                "Permintaan analitik tidak dapat diproses "
                "karena rencana query tidak valid."
            ),
            data_basis="",
            outcome="no_data",
        )

    try:
        sql = build_plan_sql(plan)
    except Exception:
        return AgentResult(
            answer=(
                "Query analitik tidak dapat dibangun "
                "dari rencana yang dihasilkan."
            ),
            data_basis="",
            outcome="no_data",
        )

    result = run_safe_query(sql)

    if not result.success:
        return AgentResult(
            answer=(
                "Data tidak dapat diperoleh karena query "
                "tidak dapat dijalankan dengan aman."
            ),
            data_basis="",
            outcome="no_data",
        )

    if not result.rows:
        return AgentResult(
            answer=(
                "Tidak ditemukan data untuk periode dan "
                "kriteria tersebut."
            ),
            data_basis="Gold dataset",
            outcome="no_data",
        )

    try:
        answer, data_basis = format_llm_answer(
            plan,
            result.rows,
        )
    except Exception:
        return AgentResult(
            answer=(
                "Data berhasil diperoleh, tetapi hasil "
                "analitik belum dapat diformat."
            ),
            data_basis="",
            outcome="no_data",
        )

    return AgentResult(
        answer=answer,
        data_basis=data_basis,
        outcome="answered",
    )


def format_llm_answer(
    plan,
    rows: list[dict],
) -> tuple[str, str]:

    if not rows:
        raise ValueError("Tidak ada row untuk diformat.")

    date_filter = (
        plan.filters.get("metric_date")
        or plan.filters.get("order_date", {})
    )

    if "between" in date_filter:
        start_date = date_filter["between"][0]
        end_date = (
            date.fromisoformat(
                date_filter["between"][1]
            )
            + timedelta(days=1)
        ).isoformat()

    elif "from" in date_filter:
        start_date = date_filter["from"]

        if "to" in date_filter:
            end_date = (
                date.fromisoformat(
                    date_filter["to"]
                )
                + timedelta(days=1)
            ).isoformat()

        elif "lt" in date_filter:
            end_date = date_filter["lt"]

        elif "lte" in date_filter:
            end_date = (
                date.fromisoformat(
                    date_filter["lte"]
                )
                + timedelta(days=1)
            ).isoformat()

        else:
            raise ValueError(
                "Date filter tidak memiliki end date."
            )

    elif "gte" in date_filter:
        start_date = date_filter["gte"]

        if "lt" in date_filter:
            end_date = date_filter["lt"]

        elif "lte" in date_filter:
            end_date = (
                date.fromisoformat(
                    date_filter["lte"]
                )
                + timedelta(days=1)
            ).isoformat()

        else:
            raise ValueError(
                "Date filter tidak memiliki end date."
            )

    else:
        raise ValueError(
            "Date filter tidak dapat dipahami."
        )

    if plan.intent == "shipments_per_carrier":
        parts = []

        for row in rows:
            parts.append(
                f"{row['carrier_id']}: "
                f"{int(row['total_shipments'])} shipment"
            )

        answer = (
            "Jumlah shipment per carrier untuk periode "
            f"{start_date} sampai sebelum {end_date}: "
            + "; ".join(parts)
            + "."
        )

        data_basis = (
            "gold.carrier_daily; "
            "SUM(shipment_count); "
            "group by carrier_id; "
            f"metric_date >= {start_date} dan < {end_date}"
        )

        return answer, data_basis

    if plan.intent == "best_on_time_carrier":
        row = rows[0]

        carrier_id = row["carrier_id"]
        on_time = int(row["on_time_delivered"])
        delivered = int(row["delivered"])
        rate = float(row["on_time_rate_pct"])

        answer = (
            f"Carrier dengan on-time rate tertinggi pada periode "
            f"{start_date} sampai sebelum {end_date} adalah "
            f"{carrier_id} dengan on-time rate {rate:.2f}% "
            f"({on_time} on-time delivered dari "
            f"{delivered} delivered)."
        )

        data_basis = (
            "gold.carrier_daily; "
            "SUM(on_time_delivered_count) / "
            "SUM(delivered_count); "
            "group by carrier_id; "
            f"metric_date >= {start_date} dan < {end_date}; "
            "minimum 20 delivered"
        )

        return answer, data_basis

    if plan.intent == "express_refund_rate":
        row = rows[0]

        refund_amount = float(
            row["refund_amount_idr"]
        )
        shipping_fee = float(
            row["shipping_fee_idr"]
        )
        refund_rate = float(
            row["refund_rate_pct"]
        )

        answer = (
            f"Refund rate untuk service level Express pada periode "
            f"{start_date} sampai sebelum {end_date} adalah "
            f"{refund_rate:.2f}%, berdasarkan refund "
            f"{format_idr(refund_amount)} dibandingkan "
            f"shipping fee {format_idr(shipping_fee)}."
        )

        data_basis = (
            "gold.shipment_fact; "
            "SUM(refund_amount_idr) / SUM(shipping_fee_idr); "
            "service_level = express; "
            f"order_date >= {start_date} dan < {end_date}"
        )

        return answer, data_basis

    if plan.intent == "weekly_comparison":
        current_start = start_date
        current_end = end_date

        current_start_date = date.fromisoformat(
            current_start
        )
        current_end_date = date.fromisoformat(
            current_end
        )

        previous_start = (
            current_start_date - timedelta(days=7)
        ).isoformat()

        previous_end = current_start

        parts = []

        for row in rows:
            carrier_id = row["carrier_id"]
            current = int(
                row["current_week_shipments"]
            )
            previous = int(
                row["previous_week_shipments"]
            )
            change = int(
                row["change_shipments"]
            )

            if previous == 0:
                change_pct_text = (
                    "persentase perubahan tidak dihitung "
                    "karena minggu sebelumnya bernilai 0"
                )
            else:
                change_pct = (
                    change / previous
                ) * 100
                change_pct_text = (
                    f"perubahan {change_pct:.2f}%"
                )

            parts.append(
                f"{carrier_id}: "
                f"{current} shipment vs {previous} shipment "
                f"({change:+d}; {change_pct_text})"
            )

        answer = (
            f"Perbandingan shipment per carrier untuk minggu "
            f"{current_start} sampai sebelum {current_end} "
            f"dengan minggu sebelumnya "
            f"{previous_start} sampai sebelum {previous_end}: "
            + "; ".join(parts)
            + "."
        )

        data_basis = (
            "gold.carrier_daily; "
            "SUM(shipment_count); "
            "group by carrier_id; "
            f"current period {current_start} sampai sebelum "
            f"{current_end}; "
            f"previous period {previous_start} sampai sebelum "
            f"{previous_end}"
        )

        return answer, data_basis

    raise ValueError(
        f"Formatter belum mendukung intent: {plan.intent}"
    )