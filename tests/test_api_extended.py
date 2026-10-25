
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def mock_agent_response(answer="Analysis completed."):
    message = MagicMock()
    message.type = "ai"
    message.content = answer

    return {"messages": [message]}


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == (
        "AI Data Analyst Agent API is running"
    )


@pytest.mark.parametrize(
    "question",
    ["", " ", "   ", "\n\t"]
)
def test_empty_questions_rejected(question):
    response = client.post(
        "/analyze",
        json={"question": question}
    )

    assert response.status_code == 422


def test_missing_question_rejected():
    response = client.post("/analyze", json={})

    assert response.status_code == 422


def test_non_string_question_rejected():
    response = client.post(
        "/analyze",
        json={"question": 123}
    )

    assert response.status_code == 422


def test_question_too_long():
    response = client.post(
        "/analyze",
        json={"question": "A" * 2001}
    )

    assert response.status_code == 422


def test_question_whitespace_trimmed():
    with patch(
        "api.main.agent.invoke",
        return_value=mock_agent_response()
    ):
        response = client.post(
            "/analyze",
            json={"question": "  Analyze sales  "}
        )

    assert response.status_code == 200
    assert response.json()["question"] == "Analyze sales"


def test_agent_error_returns_safe_message():
    with patch(
        "api.main.agent.invoke",
        side_effect=RuntimeError("Internal provider error")
    ):
        response = client.post(
            "/analyze",
            json={"question": "Analyze sales"}
        )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Unable to complete the analysis."
    )
    assert "Internal provider error" not in response.text


def test_no_data_is_not_chart():
    tool_message = MagicMock()
    tool_message.type = "tool"
    tool_message.name = "create_chart"
    tool_message.content = "The query returned no data."

    final_message = MagicMock()
    final_message.type = "ai"
    final_message.content = "No data available."

    with patch(
        "api.main.agent.invoke",
        return_value={"messages": [tool_message, final_message]}
    ):
        response = client.post(
            "/analyze",
            json={"question": "Create a chart"}
        )

    assert response.status_code == 200
    assert response.json()["charts"] == []


def test_agent_recursion_limit():
    with patch(
        "api.main.agent.invoke",
        return_value=mock_agent_response()
    ) as mock_invoke:
        response = client.post(
            "/analyze",
            json={"question": "Analyze sales"}
        )

    assert response.status_code == 200
    config = mock_invoke.call_args.kwargs["config"]

    assert config["recursion_limit"] == 15
    assert isinstance(config["configurable"]["thread_id"], str)
    assert config["configurable"]["thread_id"]

def test_cors_allowed_origin():
    response = client.options(
        "/analyze",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST"
        }
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )


def test_cors_unknown_origin():
    response = client.options(
        "/analyze",
        headers={
            "Origin": "https://unknown.example",
            "Access-Control-Request-Method": "POST"
        }
    )

    assert "access-control-allow-origin" not in response.headers


# ============================================================
# STRUCTURED SQL TABLE TESTS
# ============================================================

def mock_sql_tool_message(columns, rows):
    # create a tool message with structured sql results
    message = MagicMock()
    message.type = "tool"
    message.name = "execute_database_query"
    message.content = "SQL query completed."
    message.artifact = {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows)
    }

    return message


def test_analyze_returns_sql_table():
    # verify that the api returns structured database results
    tool_message = mock_sql_tool_message(
        columns=["month", "revenue"],
        rows=[
            {"month": "2017-08", "revenue": 573971.68},
            {"month": "2017-11", "revenue": 1010271.37}
        ]
    )

    final_message = MagicMock()
    final_message.type = "ai"
    final_message.content = "Monthly revenue analysis completed."

    with patch(
        "api.main.agent.invoke",
        return_value={"messages": [tool_message, final_message]}
    ):
        response = client.post(
            "/analyze",
            json={"question": "Show monthly revenue"}
        )

    assert response.status_code == 200

    data = response.json()

    assert "tables" in data
    assert len(data["tables"]) == 1

    table = data["tables"][0]

    assert table["columns"] == ["month", "revenue"]
    assert table["row_count"] == 2
    assert table["rows"] == [
        {"month": "2017-08", "revenue": 573971.68},
        {"month": "2017-11", "revenue": 1010271.37}
    ]


def test_analyze_returns_empty_sql_table():
    # verify that an empty query preserves column information
    tool_message = mock_sql_tool_message(
        columns=["month", "revenue"],
        rows=[]
    )

    final_message = MagicMock()
    final_message.type = "ai"
    final_message.content = "No matching records found."

    with patch(
        "api.main.agent.invoke",
        return_value={"messages": [tool_message, final_message]}
    ):
        response = client.post(
            "/analyze",
            json={"question": "Find unavailable sales"}
        )

    assert response.status_code == 200

    data = response.json()

    assert len(data["tables"]) == 1
    assert data["tables"][0]["columns"] == ["month", "revenue"]
    assert data["tables"][0]["rows"] == []
    assert data["tables"][0]["row_count"] == 0


def test_analyze_without_sql_returns_empty_tables():
    # verify that normal ai responses have no sql tables
    with patch(
        "api.main.agent.invoke",
        return_value=mock_agent_response(
            "I can help analyze your database."
        )
    ):
        response = client.post(
            "/analyze",
            json={"question": "What can you do?"}
        )

    assert response.status_code == 200

    data = response.json()

    assert data["tables"] == []
    assert data["charts"] == []
    assert data["reports"] == []
