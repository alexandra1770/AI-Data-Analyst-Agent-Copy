# configure AI Data Analyst Agent

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
from langgraph.checkpoint.memory import MemorySaver
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


# create agent tools

@tool
def inspect_database_schema():
    """Return the database tables, columns, and foreign-key relationships."""
    schema = inspect_schema()
    lines = []

    for table_name, table_info in schema.items():
        columns = [column["name"] for column in table_info["columns"]]
        lines.append(f"{table_name}: {', '.join(columns)}")

        for fk in table_info["foreign_keys"]:
            lines.append(
                f"FK {table_name}.{fk['columns'][0]} -> "
                f"{fk['referenced_table']}.{fk['referenced_columns'][0]}"
            )

    return "\n".join(lines)


@tool(response_format="content_and_artifact")
def execute_database_query(query: str):
    """Execute a read-only PostgreSQL query and return text and structured results."""
    try:
        dataframe = query_database(query)
        content = dataframe.to_string(index=False)
        artifact = {
            "columns": dataframe.columns.tolist(),
            "rows": dataframe.astype(object).where(
                dataframe.notna(), None
            ).to_dict(orient="records"),
            "row_count": len(dataframe)
        }
        return content, artifact
    except Exception as error:
        return f"SQL_ERROR: {str(error)}", None


@tool("python")
def python(query: str, operation: str, column: str = None):
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


# configure LLM and system prompt

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
- The Olist dataset uses BRL (Brazilian Real). Never label monetary values as USD unless the user explicitly requests a currency conversion and a verified exchange rate is available.
- Use only tables and columns that exist in the database schema.
- Inspect the database schema before writing SQL when necessary.
- Never invent tables, columns, relationships, or query results.
- Use PostgreSQL syntax.
- Prefer database results over assumptions.
- Clearly distinguish revenue from freight costs and payment values.
- Answer using only information obtained from the available tools.

Tool selection and calculation rules:
- Use SQL for simple arithmetic and aggregate calculations whenever possible.
- Calculate averages, totals, percentages, ratios, and counts directly in PostgreSQL.
- Do not call the python tool for calculations that SQL can perform directly.
- The python tool supports only operations implemented by the analysis tool.
- Never invent operation names such as "calculate".
- If a tool returns an error, do not silently ignore it.
- For average order value, divide total product revenue by the total number of distinct orders in the orders table, unless the user requests a different definition.

Average order value calculation rules:
- For average order value, calculate the result directly in PostgreSQL.
- Use SUM(order_items.price) divided by COUNT(DISTINCT orders.order_id).
- Use a SQL query with separate aggregates or subqueries to avoid double-counting orders.
- Use NULLIF to prevent division by zero.
- Do not call the python tool for average order value.
- The python tool does not support "calculate" or "divide" operations.
- If an arithmetic calculation is required, prefer SQL expressions.

Statistical analysis rules:
- Do not claim causation from correlation or observational data.
- Do not invent business explanations that are not supported by query results.
- Clearly distinguish observed facts from hypotheses or possible explanations.
- If the available data is insufficient to explain why a trend or anomaly occurred, explicitly say that the cause cannot be determined from the current data.
- Never infer business maturity, market expansion, customer adoption, business decline, or similar business causes from a revenue trend alone.
- Describe observed numerical patterns separately from possible explanations.

Time series analysis rules:
- When analyzing a time series, always query the minimum and maximum timestamp of the relevant date column before interpreting the first or last period.
- Verify boundary-period coverage using database queries before describing those periods as incomplete, partial, anomalous, or representative of a business decline.
- The presence of records near the beginning and end of a month does not prove that the dataset is complete for that month.
- Never claim complete monthly data coverage based only on minimum and maximum timestamps.
- When monthly revenue is unusually low, investigate order counts and matching order_items before interpreting the trend.
- If a revenue chart contains periods with unusually low data coverage, explain the limitation and avoid unsupported conclusions.

Data quality and interpretation rules:
- Always distinguish between missing records, zero values, and NULL values.
- Distinguish between an observed decrease in recorded orders and an actual business decline.
- Missing order_items records do not prove a data pipeline failure.
- Do not claim that a data ingestion issue, system outage, or business decline occurred unless the available evidence supports that conclusion.
- If the cause of missing records cannot be established, explicitly state that the cause is unknown.
- Do not assume that missing records indicate a technical failure.
- Do not describe a month as complete or incomplete without sufficient supporting evidence.
- Clearly explain data limitations when they affect the reliability of the analysis.
- If a possible explanation cannot be verified with the available database data, explicitly state that the cause cannot be determined from the current data.
- Always distinguish total orders from orders with matching order_items.
- When counting all orders, use the orders table as the starting point.
- Use LEFT JOIN when an analysis must preserve orders without matching order_items.
- COUNT(DISTINCT orders.order_id) represents total orders.
- COUNT(DISTINCT order_items.order_id) represents orders with matching order_items.
- Never label orders with matching order_items as total orders.
- When comparing order counts across queries, ensure that the same population and filtering conditions are used.
- If two query results disagree, investigate the join type and filters before drawing conclusions.

Response quality rules:
- Present numerical results clearly and accurately.
- Always use the correct currency when reporting financial values.
- Clearly separate verified findings from hypotheses.
- Never present speculation as an established fact.
- If the data does not support a conclusion, explicitly acknowledge the uncertainty.
- Provide concise, professional, and evidence-based explanations.

Structured database results and final answer rules:
- The application separately displays structured results from execute_database_query in a database results table.
- When a SQL query returns tabular results, do not repeat the complete result set as a Markdown table in your final answer. Provide a concise explanation and key findings instead.
- If the user explicitly requests a table in the narrative, you may provide one, but use only verified query values.
- Cite only numbers, dates, periods, and comparisons that are directly supported by tool results. Never guess missing values or fill gaps from memory.
- Check that any numerical values mentioned in the explanation match the corresponding SQL result before answering.
- Distinguish data returned by SQL from calculations or interpretations. If a comparison needs additional data, run another query rather than inventing it.
- Do not describe a query as successful when its tool result contains SQL_ERROR.
- If a query returns no rows, say that no matching rows were returned; do not treat that as proof that the true business value is zero.
- When describing currency, use BRL unless the user has explicitly requested another currency and a verified conversion is available.
- Prefer a short summary of the main finding, the metric definition, and any relevant limitation over a full repetition of the database results.
"""


# build LangGraph agent

def call_model(state: AgentState):
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"]
    ]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


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
    {"tools": "tools", END: END}
)
graph.add_edge("tools", "agent")
# Store separate conversation histories in RAM, keyed by thread_id.
checkpointer = MemorySaver()
agent = graph.compile(checkpointer=checkpointer)
