
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.mcp_server.server import (
    execute_database_query,
    inspect_database_schema,
)


def test_mcp_server_tools_registered():
    from src.mcp_server.server import mcp

    assert mcp.name == "AI Data Analyst PostgreSQL"


def test_mcp_execute_database_query():
    dataframe = pd.DataFrame({
        "total_orders": [99441]
    })

    with patch(
        "src.mcp_server.server.query_database",
        return_value=dataframe
    ) as mock_query:
        result = execute_database_query(
            "SELECT COUNT(*) AS total_orders FROM orders"
        )

    assert result["columns"] == ["total_orders"]
    assert result["rows"] == [{"total_orders": 99441}]
    assert result["row_count"] == 1
    mock_query.assert_called_once_with(
        "SELECT COUNT(*) AS total_orders FROM orders"
    )


@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM orders",
        "DROP TABLE orders",
        "UPDATE orders SET order_status = 'canceled'",
        "SELECT * FROM pg_catalog.pg_user",
    ]
)
def test_mcp_rejects_unsafe_queries(query):
    from src.tools.query_database import validate_query

    with pytest.raises(ValueError):
        validate_query(query)


def test_mcp_schema_contains_allowed_tables():
    inspector = MagicMock()

    inspector.get_columns.return_value = [
        {"name": "id", "type": "INTEGER", "nullable": False}
    ]

    inspector.get_foreign_keys.return_value = [
        {
            "constrained_columns": ["customer_id"],
            "referred_table": "customers",
            "referred_columns": ["customer_id"]
        }
    ]

    with patch(
        "src.mcp_server.server.inspect",
        return_value=inspector
    ):
        result = inspect_database_schema()

    assert len(result) == 9
    assert "orders" in result
    assert "customers" in result
    assert result["orders"]["columns"][0]["name"] == "id"
    assert result["orders"]["foreign_keys"][0] == {
        "columns": ["customer_id"],
        "referenced_table": "customers",
        "referenced_columns": ["customer_id"]
    }
    assert inspector.get_columns.call_count == 9
    assert inspector.get_foreign_keys.call_count == 9
