
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from api.main import app


client = TestClient(app)


def test_analyze_endpoint():
    mock_message = MagicMock()
    mock_message.type = "ai"
    mock_message.content = "Total revenue is R$ 13,591,643.70."

    mock_result = {
        "messages": [mock_message]
    }

    with patch("api.main.agent.invoke", return_value=mock_result) as mock_invoke:
        response = client.post(
            "/analyze",
            json={"question": "What is the total revenue?"}
        )

    assert response.status_code == 200

    data = response.json()

    assert data["question"] == "What is the total revenue?"
    assert data["answer"] == "Total revenue is R$ 13,591,643.70."
    assert data["charts"] == []
    assert data["reports"] == []

    mock_invoke.assert_called_once()

def test_analyze_with_chart_and_report():
    chart_message = MagicMock()
    chart_message.type = "tool"
    chart_message.name = "create_chart"
    chart_message.content = "outputs/charts/monthly_revenue.png"

    report_message = MagicMock()
    report_message.type = "tool"
    report_message.name = "export_report"
    report_message.content = "outputs/reports/sales_analysis.md"

    final_message = MagicMock()
    final_message.type = "ai"
    final_message.content = "Analysis completed successfully."

    mock_result = {
        "messages": [
            chart_message,
            report_message,
            final_message
        ]
    }

    with patch("api.main.agent.invoke", return_value=mock_result):
        response = client.post(
            "/analyze",
            json={"question": "Analyze monthly sales"}
        )

    assert response.status_code == 200

    data = response.json()

    assert data["question"] == "Analyze monthly sales"
    assert data["answer"] == "Analysis completed successfully."
    assert data["charts"] == ["/charts/monthly_revenue.png"]
    assert data["reports"] == ["/reports/sales_analysis.md"]
