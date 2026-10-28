from dataclasses import dataclass


@dataclass
class ScopeResult:
    allowed: bool
    reason: str


OUT_OF_SCOPE_PATTERNS = [
    # Weather
    "cuaca",
    "weather",
    "ramalan",

    # Medical / health
    "diagnosis",
    "obat",
    "penyakit",
    "medical",
    "health",

    # Email / external communication
    "kirim email",
    "send email",
    "email seseorang",
    "gmail",

    # Operational side effects
    "ubah status",
    "update status",
    "batalkan shipment",
    "cancel shipment",
    "hapus shipment",
    "delete shipment",

    # Credential / secret requests
    "password",
    "api key",
    "api_key",
    "token",
    "credential",
    "secret",
    "database url",
    "database_url",

    # Prompt injection / instruction override
    "ignore previous instructions",
    "ignore previous instruction",
    "ignore all previous",
    "system prompt",
    "developer message",
    "reveal your prompt",
    "show your prompt",
    "bypass security",
    "bypass sql guard",
]


def check_scope(user_message: str) -> ScopeResult:
    """
    Determine whether a user request is within the
    supported analytics scope.

    This check happens before SQL generation.
    """

    if not isinstance(user_message, str):
        return ScopeResult(
            allowed=False,
            reason="Input tidak valid",
        )

    text = user_message.strip().lower()

    if not text:
        return ScopeResult(
            allowed=False,
            reason="Pertanyaan kosong",
        )

    for pattern in OUT_OF_SCOPE_PATTERNS:
        if pattern in text:
            return ScopeResult(
                allowed=False,
                reason=(
                    "Permintaan berada di luar scope "
                    "Analytics Agent"
                ),
            )

    return ScopeResult(
        allowed=True,
        reason="Permintaan berada dalam scope awal",
    )