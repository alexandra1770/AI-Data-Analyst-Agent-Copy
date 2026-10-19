import re

import pandas as pd
from sqlalchemy import text

from src.database import engine


FORBIDDEN_KEYWORDS = [
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "grant",
    "revoke"
]


def query_database(query):
    clean_query = query.strip()

    if not clean_query:
        raise ValueError("Query cannot be empty.")

    if not clean_query.lower().startswith(("select", "with")):
        raise ValueError("Only SELECT queries are allowed.")

    query_without_final_semicolon = clean_query.rstrip(";")

    if ";" in query_without_final_semicolon:
        raise ValueError("Multiple SQL statements are not allowed.")

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", clean_query, re.IGNORECASE):
            raise ValueError(
                f"Forbidden SQL operation detected: {keyword.upper()}"
            )

    with engine.connect() as connection:
        result = pd.read_sql(text(clean_query), connection)

    return result