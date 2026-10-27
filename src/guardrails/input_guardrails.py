
import re


MAX_QUESTION_LENGTH = 2000


DANGEROUS_DATABASE_PATTERNS = [
    r"\b(?:delete|remove|erase|wipe)\s+(?:all\s+)?(?:the\s+)?(?:orders|customers|products|records|rows|data)\b",
    r"\b(?:drop|truncate)\s+(?:the\s+)?(?:table\s+)?\w+\b",
    r"\bupdate\s+(?:every|all|the)\s+\w+\s+(?:status|to|set)\b",
    r"\b(?:insert|create)\s+(?:a\s+)?(?:new\s+)?(?:record|row)\s+into\b",
]


DANGEROUS_INSTRUCTION_PATTERNS = [
    r"\bignore\s+(?:all\s+)?(?:your|previous|system)\s+instructions\b.{0,100}\b(?:reveal|show|print|expose)\b",
    r"\b(?:reveal|show|print|expose)\s+(?:your\s+)?(?:system\s+prompt|secret\s+keys?|api\s+keys?|passwords?|credentials)\b",
]


def validate_user_input(question: str) -> str:
    if not isinstance(question, str):
        raise ValueError("Question must be a string.")

    clean_question = question.strip()

    if not clean_question:
        raise ValueError("Question cannot be empty.")

    if len(clean_question) > MAX_QUESTION_LENGTH:
        raise ValueError("Question is too long.")

    explanatory_pattern = (
        r"^(?:explain|describe|what|why|how|compare|"
        r"can you explain)\b"
    )

    is_explanatory = bool(
        re.search(
            explanatory_pattern,
            clean_question,
            flags=re.IGNORECASE
        )
    )

    if not is_explanatory:
        for pattern in DANGEROUS_DATABASE_PATTERNS:
            if re.search(
                pattern,
                clean_question,
                flags=re.IGNORECASE | re.DOTALL
            ):
                raise ValueError(
                    "Database modification requests are not allowed."
                )

    for pattern in DANGEROUS_INSTRUCTION_PATTERNS:
        if re.search(
            pattern,
            clean_question,
            flags=re.IGNORECASE | re.DOTALL
        ):
            raise ValueError(
                "Requests to reveal protected instructions or secrets are not allowed."
            )

    return clean_question
