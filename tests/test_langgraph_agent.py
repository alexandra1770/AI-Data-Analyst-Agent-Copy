
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src import agent as agent_module


def test_agent_has_required_tools():
    tool_names = {tool.name for tool in agent_module.tools}

    assert "inspect_database_schema" in tool_names
    assert "execute_database_query" in tool_names
    assert "python" in tool_names
    assert "create_chart" in tool_names
    assert "export_report" in tool_names


def test_agent_stops_without_tool_calls():
    state = {
        "messages": [
            AIMessage(content="Analysis completed.")
        ]
    }

    result = agent_module.should_continue(state)

    assert result == "__end__"


def test_agent_continues_with_tool_calls():
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "inspect_database_schema",
                "args": {},
                "id": "call_1"
            }
        ]
    )

    state = {"messages": [message]}

    result = agent_module.should_continue(state)

    assert result == "tools"


def test_system_prompt_contains_revenue_rule():
    assert "SUM(order_items.price)" in agent_module.SYSTEM_PROMPT
    assert "payments.payment_value" in agent_module.SYSTEM_PROMPT


def test_system_prompt_requires_database_evidence():
    prompt = agent_module.SYSTEM_PROMPT

    assert "Never invent tables" in prompt
    assert "Do not claim causation from correlation" in prompt
    assert "cause cannot be determined" in prompt


def test_call_model_includes_system_prompt(monkeypatch):
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(
        content="Analysis completed."
    )

    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        fake_llm
    )

    state = {
        "messages": [
            HumanMessage(content="Analyze revenue.")
        ]
    }

    result = agent_module.call_model(state)

    messages = fake_llm.invoke.call_args.args[0]

    assert messages[0].type == "system"
    assert messages[1].type == "human"
    assert result["messages"][0].content == "Analysis completed."


def test_agent_final_response(monkeypatch):
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(
        content="Total revenue is 1000 BRL."
    )

    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        fake_llm
    )

    result = agent_module.agent.invoke(
        {
            "messages": [
                HumanMessage(content="What is the revenue?")
            ]
        },
        config={
            "configurable": {
                "thread_id": "test-final-response"
            }
        }
    )

    assert result["messages"][-1].content == "Total revenue is 1000 BRL."


def test_agent_executes_tool_and_continues(monkeypatch):
    fake_llm = MagicMock()

    fake_llm.invoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "inspect_database_schema",
                    "args": {},
                    "id": "call_schema"
                }
            ]
        ),
        AIMessage(
            content="The database contains an orders table."
        )
    ]

    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        fake_llm
    )

    monkeypatch.setattr(
        agent_module,
        "inspect_schema",
        lambda: {
            "orders": {
                "columns": [{"name": "order_id"}],
                "foreign_keys": []
            }
        }
    )

    result = agent_module.agent.invoke(
        {
            "messages": [
                HumanMessage(content="Inspect the database.")
            ]
        },
        config={
            "configurable": {
                "thread_id": "test-executes-tool"
            }
        }
    )

    tool_messages = [
        message
        for message in result["messages"]
        if isinstance(message, ToolMessage)
    ]

    assert len(tool_messages) == 1
    assert "orders" in tool_messages[0].content
    assert result["messages"][-1].content == (
        "The database contains an orders table."
    )
    assert fake_llm.invoke.call_count == 2


def test_agent_handles_sql_tool_error(monkeypatch):
    fake_llm = MagicMock()

    fake_llm.invoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "execute_database_query",
                    "args": {"query": "SELECT * FROM missing_table"},
                    "id": "call_sql"
                }
            ]
        ),
        AIMessage(
            content="The query could not be completed."
        )
    ]

    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        fake_llm
    )

    def fake_mcp_tool(tool_name, arguments=None):
        raise ValueError("Table does not exist.")

    monkeypatch.setattr(
        agent_module,
        "call_mcp_tool",
        fake_mcp_tool
    )
    result = agent_module.agent.invoke(
        {
            "messages": [
                HumanMessage(content="Query a missing table.")
            ]
        },
        config={
            "configurable": {
                "thread_id": "test-sql-error"
            }
        }
    )

    tool_messages = [
        message
        for message in result["messages"]
        if isinstance(message, ToolMessage)
    ]

    assert len(tool_messages) == 1
    assert "SQL_ERROR" in tool_messages[0].content
    assert result["messages"][-1].content == (
        "The query could not be completed."
    )
