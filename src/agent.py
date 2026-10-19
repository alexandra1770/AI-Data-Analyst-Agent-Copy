#configure AI Data Analyst Agent

import os
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from src.tools.inspect_schema import inspect_schema
from src.tools.query_database import query_database
from src.tools.python_analysis import analyze_query_result
from src.tools.create_chart import create_chart_from_query
from src.tools.export_report import export_analysis_report


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY was not found in the .env file.")


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
#create agent tools

@tool
def inspect_database_schema():
    """Return the database tables, columns, and foreign-key relationships."""
    schema = inspect_schema()

    lines = []

    for table_name, table_info in schema.items():
        columns = [
            column["name"]
            for column in table_info["columns"]
        ]

        lines.append(
            f"{table_name}: {', '.join(columns)}"
        )

        for fk in table_info["foreign_keys"]:
            lines.append(
                f"FK {table_name}.{fk['columns'][0]} -> "
                f"{fk['referenced_table']}.{fk['referenced_columns'][0]}"
            )

    return "\n".join(lines)


@tool
def execute_database_query(query: str):
    """Execute a read-only PostgreSQL query and return the result."""
    try:
        return query_database(query).to_string(index=False)

    except Exception as error:
        return f"SQL_ERROR: {str(error)}"


@tool("python")
def python(
    query: str,
    operation: str,
    column: str = None
):
    """Analyze PostgreSQL query results using Pandas for statistics and correlations."""
    try:
        if operation in ["corr", "cor"]:
            operation = "correlation"

        return analyze_query_result(
            query=query,
            operation=operation,
            column=column
        )

    except Exception as error:
        return f"PYTHON_ANALYSIS_ERROR: {str(error)}"


@tool
def create_chart(
    query: str,
    chart_type: str,
    x_column: str,
    y_column: str,
    title: str = "Data Analysis",
    filename: str = "chart.png"
):
    """Create a chart from PostgreSQL data and save it as an image."""
    try:
        return create_chart_from_query(
            query=query,
            chart_type=chart_type,
            x_column=x_column,
            y_column=y_column,
            title=title,
            filename=filename
        )

    except Exception as error:
        return f"CHART_ERROR: {str(error)}"


@tool
def export_report(
    title: str,
    question: str,
    analysis: str,
    chart_path: str = None,
    filename: str = "analysis_report.md"
):
    """Export an analysis result as a Markdown report, optionally including a chart."""
    try:
        return export_analysis_report(
            title=title,
            question=question,
            analysis=analysis,
            chart_path=chart_path,
            filename=filename
        )

    except Exception as error:
        return f"REPORT_ERROR: {str(error)}"
#configure LLM and system prompt

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    max_tokens=2048,
    reasoning_effort="low",
    api_key=groq_api_key
)


tools = [
    inspect_database_schema,
    execute_database_query,
    python,
    create_chart,
    export_report
]

llm_with_tools = llm.bind_tools(tools)


SYSTEM_PROMPT = """
You are an AI Data Analyst working with a PostgreSQL e-commerce database.

Use the available tools to inspect the database schema and execute read-only SQL queries.

Business rules:
- Revenue means product revenue and must be calculated as SUM(order_items.price).
- When calculating revenue, include all order_items by default.
- Do not filter by order_status unless the user explicitly asks for delivered, canceled, shipped, or another specific order status.
- Do not use payments.payment_value as revenue unless the user explicitly asks about payments or total paid amounts.
- Use only tables and columns that exist in the database schema.
- Inspect the database schema before writing SQL when necessary.
- Never invent tables, columns, relationships, or query results.
- Use PostgreSQL syntax.
- Prefer database results over assumptions.
- Clearly distinguish revenue from freight costs and payment values.
- Answer using only information obtained from the available tools.
- Do not claim causation from correlation or observational data.
- Do not invent business explanations that are not supported by query results.
- Clearly distinguish observed facts from hypotheses or possible explanations.
- If the available data is insufficient to explain why a trend or anomaly occurred, explicitly say that the cause cannot be determined from the current data.
- When analyzing a time series, always query the minimum and maximum timestamp of the relevant date column before interpreting the first or last period.
- You must verify whether boundary periods are complete using a database query before describing them as incomplete, partial, anomalous, or representative of a business decline.
- Never infer business maturity, market expansion, customer adoption, business decline, or similar business causes from a revenue trend alone.
- Describe observed numerical patterns separately from possible explanations.
- If a possible explanation cannot be verified with the available database data, explicitly state that the cause cannot be determined from the current data.
"""

#build LangGraph agent

def call_model(state: AgentState):
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"]
    ]

    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response]
    }


def should_continue(state: AgentState):
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return END


graph = StateGraph(AgentState)

graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(tools))

graph.add_edge(START, "agent")

graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)

graph.add_edge("tools", "agent")

agent = graph.compile()