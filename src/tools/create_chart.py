
from pathlib import Path
from uuid import uuid4

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from pandas.api.types import is_numeric_dtype

from src.tools.query_database import query_database


BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "charts"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_CHARTS = {"line", "bar", "scatter"}


def create_chart_from_query(
    query,
    chart_type,
    x_column,
    y_column,
    title="Data Analysis",
    filename="chart.png"
):
    if chart_type not in SUPPORTED_CHARTS:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    df = query_database(query)

    if df.empty:
        return "The query returned no data."

    if x_column not in df.columns:
        raise ValueError(f"Column not found: {x_column}")

    if y_column not in df.columns:
        raise ValueError(f"Column not found: {y_column}")

    if not is_numeric_dtype(df[y_column]):
        raise ValueError(f"Column '{y_column}' must be numeric.")

    if df[y_column].dropna().empty:
        raise ValueError(f"Column '{y_column}' has no valid numeric values.")

    if chart_type == "scatter" and not is_numeric_dtype(df[x_column]):
        raise ValueError(f"Column '{x_column}' must be numeric for scatter charts.")

    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("Invalid chart filename.")

    if Path(filename).name != filename:
        raise ValueError("Invalid chart filename.")

    if Path(filename).suffix.lower() != ".png":
        raise ValueError("Chart filename must end with .png.")

    output_path = OUTPUT_DIR / f"{Path(filename).stem}_{uuid4().hex[:12]}.png"

    fig, ax = plt.subplots(figsize=(10, 6))

    try:
        if chart_type == "line":
            ax.plot(df[x_column], df[y_column], marker="o")

        elif chart_type == "bar":
            ax.bar(df[x_column], df[y_column])

        elif chart_type == "scatter":
            ax.scatter(df[x_column], df[y_column])

        ax.set_title(title)
        ax.set_xlabel(x_column)
        ax.set_ylabel(y_column)
        ax.tick_params(axis="x", labelrotation=45)

        fig.tight_layout()
        fig.savefig(output_path, dpi=150)

    finally:
        plt.close(fig)

    return str(output_path)
