
import os
import re


SENSITIVE_ENV_KEYS = (
    "GROQ_API_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "DATABASE_URL",
    "POSTGRES_PASSWORD",
)

SECRET_PATTERNS = [
    re.compile(r"\bgsk_[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bsk-lf-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bpk-lf-[A-Za-z0-9_-]{12,}\b"),
    re.compile(
        r"(?i)\b(?:postgresql|postgres)://[^\s\"'<>]+"
    ),
]


def validate_agent_output(answer: str) -> str:
    if not isinstance(answer, str):
        raise ValueError("Agent output must be a string.")

    if not answer.strip():
        raise ValueError("Agent output cannot be empty.")

    for key in SENSITIVE_ENV_KEYS:
        value = os.getenv(key)

        if value and len(value) >= 8 and value in answer:
            raise ValueError("Agent output contains sensitive information.")

    for pattern in SECRET_PATTERNS:
        if pattern.search(answer):
            raise ValueError("Agent output contains sensitive information.")

    return answer
