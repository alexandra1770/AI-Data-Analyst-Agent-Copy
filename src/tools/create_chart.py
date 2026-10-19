#create charts from database data 

from pathlib import Path

import matplotlib.pyplot as plt

from src.tools.query_database import query_database


BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "charts"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_chart_from_query(
    query,
    chart_type,
    x_column,
    y_column,
    title="Data Analysis",
    filename="chart.png"
):
    df = query_database(query)

    if df.empty:
        return "The query returned no data."

    if x_column not in df.columns:
        raise ValueError(f"Column not found: {x_column}")

    if y_column not in df.columns:
        raise ValueError(f"Column not found: {y_column}")

    plt.figure(figsize=(10, 6))

    if chart_type == "line":
        plt.plot(df[x_column], df[y_column], marker="o")

    elif chart_type == "bar":
        plt.bar(df[x_column], df[y_column])

    elif chart_type == "scatter":
        plt.scatter(df[x_column], df[y_column])

    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    plt.title(title)
    plt.xlabel(x_column)
    plt.ylabel(y_column)
    plt.xticks(rotation=45)
    plt.tight_layout()

    output_path = OUTPUT_DIR / filename

    plt.savefig(output_path, dpi=150)
    plt.close()

    return str(output_path)