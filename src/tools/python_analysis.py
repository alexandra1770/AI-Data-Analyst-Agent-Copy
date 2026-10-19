#Python data analysis

import pandas as pd

from src.tools.query_database import query_database


def analyze_query_result(query, operation, column=None):
    df = query_database(query)

    if df.empty:
        return "The query returned no data."

    if operation == "describe":
        return df.describe(include="all").to_string()

    if operation == "mean":
        if column not in df.columns:
            raise ValueError(f"Column not found: {column}")

        return f"{column} mean: {df[column].mean():.2f}"

    if operation == "median":
        if column not in df.columns:
            raise ValueError(f"Column not found: {column}")

        return f"{column} median: {df[column].median():.2f}"

    if operation == "correlation":
        numeric_df = df.select_dtypes(include="number")

        if numeric_df.shape[1] < 2:
            return "At least two numeric columns are required."

        return numeric_df.corr().to_string()

    raise ValueError(f"Unsupported operation: {operation}")