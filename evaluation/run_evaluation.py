
import json
import re
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from src.agent import agent
from src.tools.query_database import query_database
from src.tools.inspect_schema import inspect_schema


BASE_DIR = Path(__file__).resolve().parent
TEST_CASES_PATH = BASE_DIR / "test_cases.json"
RESULTS_PATH = BASE_DIR / "results.json"


REFERENCE_QUERIES = {
    "order_count": """
        SELECT COUNT(DISTINCT order_id) AS value
        FROM orders
    """,
    "total_revenue": """
        SELECT SUM(price) AS value
        FROM order_items
    """,
    "average_order_value": """
        SELECT
            (SELECT SUM(price) FROM order_items)
            /
            NULLIF(
                (SELECT COUNT(DISTINCT order_id) FROM orders),
                0
            ) AS value
    """,
    "orders_without_items": """
        SELECT COUNT(*) AS value
        FROM orders o
        WHERE NOT EXISTS (
            SELECT 1
            FROM order_items oi
            WHERE oi.order_id = o.order_id
        )
    """,
}


def normalize_number(value):
    # Elimina separatorii de mii si normalizeaza zecimalele
    cleaned = re.sub(r"[\s\u202f\u00a0]", "", value)

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) == 3:
            cleaned = "".join(parts)
        else:
            cleaned = cleaned.replace(",", ".")

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def extract_numbers(answer):
    # Extrage valori numerice din raspuns
    pattern = r"(?<!\w)\d+(?:[.,]\d+)*"
    matches = re.findall(pattern, answer)

    numbers = []

    for match in matches:
        value = normalize_number(match)
        if value is not None:
            numbers.append(value)

    return numbers


def check_numeric_result(answer, validation_type):
    query = REFERENCE_QUERIES[validation_type]
    dataframe = query_database(query)

    if dataframe.empty or dataframe.iloc[0]["value"] is None:
        return False, "SQL reference returned no value"

    expected = Decimal(str(dataframe.iloc[0]["value"]))
    numbers = extract_numbers(answer)

    if not numbers:
        return False, "No numeric values found in the answer"

    # Permite rotunjirea la doua zecimale
    tolerance = Decimal("0.01")

    for actual in numbers:
        if abs(actual - expected) <= tolerance:
            return True, f"Verified: {actual} (SQL: {expected})"

    return False, (
        f"Numeric mismatch. Expected {expected}; "
        f"found {numbers}"
    )


def check_schema_result(answer):
    schema = inspect_schema()
    table_names = list(schema.keys())

    if not table_names:
        return False, "No tables found in schema"

    answer_lower = answer.lower()

    matched = [
        name for name in table_names
        if name.lower() in answer_lower
    ]

    if not matched:
        return False, "No database table names found in answer"

    return True, (
        f"Matched {len(matched)}/{len(table_names)} tables"
    )


def evaluate_case(test_case):
    question = test_case["question"]
    expected_tool = test_case["expected_tool"]
    validation_type = test_case["validation_type"]

    # Conversatie separata pentru fiecare test
    thread_id = f"eval-{uuid.uuid4().hex}"
    start_time = time.perf_counter()

    try:
        result = agent.invoke(
            {"messages": [HumanMessage(content=question)]},
            config={
                "configurable": {"thread_id": thread_id},
                "recursion_limit": 20,
            },
        )

        duration = round(time.perf_counter() - start_time, 2)
        messages = result["messages"]

        used_tools = []
        errors = []

        for message in messages:
            if isinstance(message, AIMessage):
                for tool_call in message.tool_calls:
                    used_tools.append(tool_call["name"])

            if isinstance(message, ToolMessage):
                content = str(message.content)

                if any(
                    marker in content
                    for marker in [
                        "SQL_ERROR:",
                        "PYTHON_ANALYSIS_ERROR:",
                        "CHART_ERROR:",
                        "REPORT_ERROR:",
                    ]
                ):
                    errors.append(content[:500])

        final_answer = str(messages[-1].content)
        tool_match = expected_tool in used_tools

        if validation_type == "schema":
            numeric_match, numeric_details = check_schema_result(
                final_answer
            )
        elif validation_type in REFERENCE_QUERIES:
            numeric_match, numeric_details = check_numeric_result(
                final_answer,
                validation_type,
            )
        else:
            numeric_match = False
            numeric_details = "Unknown validation type"

        passed = (
            tool_match
            and not errors
            and bool(final_answer.strip())
            and numeric_match
        )

        return {
            "id": test_case["id"],
            "question": question,
            "validation_type": validation_type,
            "expected_tool": expected_tool,
            "used_tools": used_tools,
            "tool_match": tool_match,
            "numeric_match": numeric_match,
            "numeric_details": numeric_details,
            "errors": errors,
            "duration_seconds": duration,
            "answer": final_answer,
            "status": "PASS" if passed else "FAIL",
        }

    except Exception as error:
        return {
            "id": test_case["id"],
            "question": question,
            "validation_type": validation_type,
            "expected_tool": expected_tool,
            "used_tools": [],
            "tool_match": False,
            "numeric_match": False,
            "numeric_details": None,
            "errors": [str(error)],
            "duration_seconds": round(
                time.perf_counter() - start_time, 2
            ),
            "answer": "",
            "status": "ERROR",
        }


def main():
    with open(TEST_CASES_PATH, encoding="utf-8") as file:
        test_cases = json.load(file)

    results = []

    print("\n=== AI DATA ANALYST - LLM EVALUATION ===\n")

    for test_case in test_cases:
        print(f"Running {test_case['id']}...")

        result = evaluate_case(test_case)
        results.append(result)

        print(f"Status: {result['status']}")
        print(f"Tools: {result['used_tools']}")
        print(f"Validation: {result['numeric_details']}")
        print(f"Duration: {result['duration_seconds']}s\n")

    passed = sum(
        result["status"] == "PASS"
        for result in results
    )

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_tests": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(
            passed / len(results) * 100, 2
        ) if results else 0,
        "results": results,
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("=== FINAL RESULTS ===")
    print(f"Passed: {passed}/{len(results)}")
    print(f"Pass rate: {report['pass_rate']}%")
    print(f"Report saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
