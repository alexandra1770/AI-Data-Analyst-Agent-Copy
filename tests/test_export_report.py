
from pathlib import Path

import pytest

from src.tools import export_report


@pytest.fixture
def report_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(export_report, "OUTPUT_DIR", tmp_path)
    return tmp_path


def generate_report(**kwargs):
    return export_report.export_analysis_report(
        title="Sales Analysis",
        question="What is the total revenue?",
        analysis="Total revenue is 1000 BRL.",
        **kwargs
    )


def test_report_creation(report_folder):
    result = generate_report()

    path = Path(result)

    assert path.exists()
    assert path.suffix == ".md"
    assert path.parent == report_folder


def test_report_content(report_folder):
    result = generate_report()

    content = Path(result).read_text(encoding="utf-8")

    assert "# Sales Analysis" in content
    assert "## User Question" in content
    assert "What is the total revenue?" in content
    assert "## Analysis" in content
    assert "Total revenue is 1000 BRL." in content


def test_report_contains_timestamp(report_folder):
    result = generate_report()

    content = Path(result).read_text(encoding="utf-8")

    assert "## Report Information" in content
    assert "Generated:" in content


def test_report_with_chart(report_folder):
    result = generate_report(
        chart_path="outputs/charts/revenue.png"
    )

    content = Path(result).read_text(encoding="utf-8")

    assert "## Chart" in content
    assert "![Analysis Chart](../charts/revenue.png)" in content


def test_report_without_chart(report_folder):
    result = generate_report()

    content = Path(result).read_text(encoding="utf-8")

    assert "## Chart" not in content


@pytest.mark.parametrize(
    "filename",
    [
        "../outside.md",
        "folder/report.md",
        "report.txt",
        ""
    ]
)
def test_invalid_filename(filename, report_folder):
    with pytest.raises(ValueError, match="filename"):
        generate_report(filename=filename)


def test_unique_report_filenames(report_folder):
    first = generate_report(filename="sales.md")
    second = generate_report(filename="sales.md")

    assert first != second
    assert Path(first).exists()
    assert Path(second).exists()


def test_report_uses_utf8(report_folder):
    result = export_report.export_analysis_report(
        title="Analiză vânzări",
        question="Care este valoarea vânzărilor?",
        analysis="Vânzările au crescut."
    )

    content = Path(result).read_text(encoding="utf-8")

    assert "Analiză vânzări" in content
    assert "Vânzările au crescut." in content


def test_report_with_custom_filename(report_folder):
    result = generate_report(filename="monthly_sales.md")

    assert Path(result).name.startswith("monthly_sales_")
    assert Path(result).suffix == ".md"


def test_report_returns_string_path(report_folder):
    result = generate_report()

    assert isinstance(result, str)
    assert Path(result).is_file()
