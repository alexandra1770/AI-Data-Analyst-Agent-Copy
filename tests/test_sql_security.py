
import pytest

from src.tools.query_database import validate_query


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM orders",
        "SELECT COUNT(*) FROM orders",
        "SELECT SUM(price) FROM order_items",
        "WITH totals AS (SELECT price FROM order_items) SELECT * FROM totals",
    ],
)
def test_valid_select_queries(query):
    assert validate_query(query) == query


@pytest.mark.parametrize(
    "query",
    [
        "",
        "   ",
        "DELETE FROM orders",
        "DROP TABLE orders",
        "UPDATE orders SET order_status = 'canceled'",
        "INSERT INTO orders DEFAULT VALUES",
        "CREATE TABLE test (id INT)",
        "SELECT * FROM orders; DROP TABLE orders",
        "WITH deleted AS (DELETE FROM orders RETURNING *) SELECT * FROM deleted",
        "SELECT * INTO TEMP TABLE backup FROM orders",
        "SELECT * FROM orders FOR UPDATE",
    ],
)
def test_unsafe_queries_are_rejected(query):
    with pytest.raises(ValueError):
        validate_query(query)


def test_invalid_sql_is_rejected():
    with pytest.raises(ValueError):
        validate_query("SELECT FROM WHERE")
