
import pandas as pd
import pytest

from src.tools import python_analysis


@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "price": [100, 200, 300, 400],
        "quantity": [1, 2, 3, 4],
        "category": ["A", "B", "A", "B"]
    })


def test_mean(monkeypatch, sample_data):
    monkeypatch.setattr(
        python_analysis,
        "query_database",
        lambda query: sample_data
    )

    result = python_analysis.analyze_query_result(
        "SELECT * FROM test",
        "mean",
        "price"
    )

    assert result == "price mean: 250.00"


def test_median(monkeypatch, sample_data):
    monkeypatch.setattr(
        python_analysis,
        "query_database",
        lambda query: sample_data
    )

    result = python_analysis.analyze_query_result(
        "SELECT * FROM test",
        "median",
        "price"
    )

    assert result == "price median: 250.00"


def test_describe(monkeypatch, sample_data):
    monkeypatch.setattr(
        python_analysis,
        "query_database",
        lambda query: sample_data
    )

    result = python_analysis.analyze_query_result(
        "SELECT * FROM test",
        "describe"
    )

    assert "price" in result
    assert "quantity" in result
    assert "mean" in result


def test_correlation(monkeypatch, sample_data):
    monkeypatch.setattr(
        python_analysis,
        "query_database",
        lambda query: sample_data
    )

    result = python_analysis.analyze_query_result(
        "SELECT * FROM test",
        "correlation"
    )

    assert "price" in result
    assert "quantity" in result
    assert "1.0" in result


def test_empty_dataframe(monkeypatch):
    monkeypatch.setattr(
        python_analysis,
        "query_database",
        lambda query: pd.DataFrame()
    )

    result = python_analysis.analyze_query_result(
        "SELECT * FROM test",
        "mean",
        "price"
    )

    assert result == "The query returned no data."


def test_missing_column_mean(monkeypatch, sample_data):
    monkeypatch.setattr(
        python_analysis,
        "query_database",
        lambda query: sample_data
    )

    with pytest.raises(ValueError, match="Column not found"):
        python_analysis.analyze_query_result(
            "SELECT * FROM test",
            "mean",
            "missing_column"
        )


def test_missing_column_median(monkeypatch, sample_data):
    monkeypatch.setattr(
        python_analysis,
        "query_database",
        lambda query: sample_data
    )

    with pytest.raises(ValueError, match="Column not found"):
        python_analysis.analyze_query_result(
            "SELECT * FROM test",
            "median",
            "missing_column"
        )


def test_correlation_with_one_numeric_column(monkeypatch):
    df = pd.DataFrame({
        "price": [100, 200, 300],
        "category": ["A", "B", "C"]
    })

    monkeypatch.setattr(
        python_analysis,
        "query_database",
        lambda query: df
    )

    result = python_analysis.analyze_query_result(
        "SELECT * FROM test",
        "correlation"
    )

    assert result == "At least two numeric columns are required."


def test_unsupported_operation(monkeypatch, sample_data):
    monkeypatch.setattr(
        python_analysis,
        "query_database",
        lambda query: sample_data
    )

    with pytest.raises(ValueError, match="Unsupported operation"):
        python_analysis.analyze_query_result(
            "SELECT * FROM test",
            "unknown"
        )

def test_mean_with_text_column(monkeypatch):
    df = pd.DataFrame({
        "category": ["Electronics", "Fashion", "Beauty"]
    })

    monkeypatch.setattr(
        python_analysis,
        "query_database",
        lambda query: df
    )

    with pytest.raises(ValueError, match="must be numeric"):
        python_analysis.analyze_query_result(
            "SELECT category FROM products",
            "mean",
            "category"
        )


def test_mean_with_all_nan_values(monkeypatch):
    df = pd.DataFrame({
        "price": [float("nan"), float("nan")]
    })

    monkeypatch.setattr(
        python_analysis,
        "query_database",
        lambda query: df
    )

    with pytest.raises(ValueError, match="no valid numeric values"):
        python_analysis.analyze_query_result(
            "SELECT price FROM products",
            "mean",
            "price"
        )
