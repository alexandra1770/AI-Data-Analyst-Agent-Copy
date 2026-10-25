
import pandas as pd
from pandas.api.types import is_numeric_dtype

from src.tools.query_database import query_database


def analyze_query_result(query, operation, column=None):
    df = query_database(query)

    if df.empty:
        return "The query returned no data."

    if operation == "describe":
        return df.describe(include="all").to_string()

    if operation in ["mean", "median"]:
        if column not in df.columns:
            raise ValueError(f"Column not found: {column}")

        if not is_numeric_dtype(df[column]):
            raise ValueError(f"Column '{column}' must be numeric.")

        valid_values = df[column].dropna()

        if valid_values.empty:
            raise ValueError(
                f"Column '{column}' has no valid numeric values."
            )

        if operation == "mean":
            result = valid_values.mean()
        else:
            result = valid_values.median()

        return f"{column} {operation}: {result:.2f}"

    if operation == "correlation":
        numeric_df = df.select_dtypes(include="number")

        if numeric_df.shape[1] < 2:
            return "At least two numeric columns are required."

        return numeric_df.corr().to_string()

    raise ValueError(f"Unsupported operation: {operation}")
