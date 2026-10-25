
from pathlib import Path

import pandas as pd
import pytest
import matplotlib.pyplot as plt

from src.tools import create_chart


@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "month": ["Jan", "Feb", "Mar"],
        "revenue": [1000, 1500, 2000],
        "quantity": [10, 15, 20]
    })


@pytest.fixture
def chart_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(create_chart, "OUTPUT_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def mock_database(monkeypatch, sample_data):
    monkeypatch.setattr(
        create_chart,
        "query_database",
        lambda query: sample_data
    )


@pytest.mark.parametrize("chart_type", ["line", "bar"])
def test_chart_generation(
    chart_type, mock_database, chart_folder
):
    result = create_chart.create_chart_from_query(
        "SELECT * FROM sales",
        chart_type,
        "month",
        "revenue",
        filename="sales.png"
    )

    path = Path(result)

    assert path.exists()
    assert path.suffix == ".png"
    assert path.stat().st_size > 0
    assert path.parent == chart_folder


def test_scatter_chart(mock_database, chart_folder):
    result = create_chart.create_chart_from_query(
        "SELECT * FROM sales",
        "scatter",
        "quantity",
        "revenue"
    )

    assert Path(result).exists()


def test_empty_data(monkeypatch, chart_folder):
    monkeypatch.setattr(
        create_chart,
        "query_database",
        lambda query: pd.DataFrame()
    )

    result = create_chart.create_chart_from_query(
        "SELECT * FROM sales",
        "bar",
        "month",
        "revenue"
    )

    assert result == "The query returned no data."
    assert list(chart_folder.iterdir()) == []


def test_missing_x_column(mock_database, chart_folder):
    with pytest.raises(ValueError, match="Column not found"):
        create_chart.create_chart_from_query(
            "SELECT * FROM sales",
            "bar",
            "missing",
            "revenue"
        )


def test_missing_y_column(mock_database, chart_folder):
    with pytest.raises(ValueError, match="Column not found"):
        create_chart.create_chart_from_query(
            "SELECT * FROM sales",
            "bar",
            "month",
            "missing"
        )


def test_invalid_chart_type(mock_database, chart_folder):
    with pytest.raises(ValueError, match="Unsupported chart type"):
        create_chart.create_chart_from_query(
            "SELECT * FROM sales",
            "pie",
            "month",
            "revenue"
        )


def test_non_numeric_y_column(mock_database, chart_folder):
    with pytest.raises(ValueError, match="must be numeric"):
        create_chart.create_chart_from_query(
            "SELECT * FROM sales",
            "bar",
            "revenue",
            "month"
        )


def test_scatter_requires_numeric_x(mock_database, chart_folder):
    with pytest.raises(ValueError, match="must be numeric"):
        create_chart.create_chart_from_query(
            "SELECT * FROM sales",
            "scatter",
            "month",
            "revenue"
        )


def test_all_nan_y_values(monkeypatch, chart_folder):
    df = pd.DataFrame({
        "month": ["Jan", "Feb"],
        "revenue": [float("nan"), float("nan")]
    })

    monkeypatch.setattr(
        create_chart,
        "query_database",
        lambda query: df
    )

    with pytest.raises(ValueError, match="no valid numeric values"):
        create_chart.create_chart_from_query(
            "SELECT * FROM sales",
            "bar",
            "month",
            "revenue"
        )


@pytest.mark.parametrize(
    "filename",
    [
        "../outside.png",
        "folder/chart.png",
        "chart.txt",
        ""
    ]
)
def test_invalid_filename(
    filename, mock_database, chart_folder
):
    with pytest.raises(ValueError, match="filename"):
        create_chart.create_chart_from_query(
            "SELECT * FROM sales",
            "bar",
            "month",
            "revenue",
            filename=filename
        )


def test_unique_chart_filenames(mock_database, chart_folder):
    first = create_chart.create_chart_from_query(
        "SELECT * FROM sales",
        "bar",
        "month",
        "revenue",
        filename="sales.png"
    )

    second = create_chart.create_chart_from_query(
        "SELECT * FROM sales",
        "bar",
        "month",
        "revenue",
        filename="sales.png"
    )

    assert first != second
    assert Path(first).exists()
    assert Path(second).exists()


def test_matplotlib_figures_are_closed(mock_database, chart_folder):
    before = set(plt.get_fignums())

    create_chart.create_chart_from_query(
        "SELECT * FROM sales",
        "line",
        "month",
        "revenue"
    )

    after = set(plt.get_fignums())

    assert after == before
