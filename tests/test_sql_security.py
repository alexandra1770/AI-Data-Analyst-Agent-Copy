
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


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM pg_catalog.pg_user",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM secret_table",
        "SELECT * FROM orders JOIN secret_table ON TRUE",
        "WITH hidden AS (SELECT * FROM secret_table) SELECT * FROM hidden",
    ],
)
def test_unauthorized_tables_are_rejected(query):
    with pytest.raises(ValueError):
        validate_query(query)


@pytest.mark.parametrize(
    "query",
    [
        "SELECT pg_sleep(10)",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT set_config('search_path', 'public', false)",
    ],
)
def test_dangerous_functions_are_rejected(query):
    with pytest.raises(ValueError):
        validate_query(query)
