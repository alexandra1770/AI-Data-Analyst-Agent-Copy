
from pathlib import Path
from datetime import datetime
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def export_analysis_report(
    title,
    question,
    analysis,
    chart_path=None,
    filename="analysis_report.md"
):
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("Invalid report filename.")

    if Path(filename).name != filename:
        raise ValueError("Invalid report filename.")

    if Path(filename).suffix.lower() != ".md":
        raise ValueError("Report filename must end with .md.")

    output_path = OUTPUT_DIR / (
        f"{Path(filename).stem}_{uuid4().hex[:12]}.md"
    )

    report_content = f"""# {title}

## User Question

{question}

## Analysis

{analysis}
"""

    if chart_path:
        chart_name = Path(chart_path).name
        report_content += f"""
## Chart

![Analysis Chart](../charts/{chart_name})
"""

    report_content += f"""
## Report Information

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    output_path.write_text(
        report_content,
        encoding="utf-8"
    )

    return str(output_path)
