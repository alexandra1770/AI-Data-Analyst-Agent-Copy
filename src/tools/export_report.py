#export analysis report

from pathlib import Path
from datetime import datetime


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
    output_path = OUTPUT_DIR / filename

    report_content = f"""# {title}

## User Question

{question}

## Analysis

{analysis}
"""

    if chart_path:
        report_content += f"""
## Chart

![Analysis Chart]({chart_path})
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