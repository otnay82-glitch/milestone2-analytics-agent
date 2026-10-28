from dataclasses import dataclass, field


@dataclass
class AnalyticsPlan:
    intent: str
    table: str
    metric: str
    filters: dict[str, str] = field(default_factory=dict)
    group_by: list[str] = field(default_factory=list)
    order_by: str = ""
    limit: int = 100
    needs_clarification: bool = False
    clarification_question: str = ""


SUPPORTED_INTENTS = {
    "shipments_per_carrier",
    "best_on_time_carrier",
    "express_refund_rate",
    "weekly_city_shipments",
    "weekly_comparison",
}