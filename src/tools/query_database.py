import pandas as pd
from pglast import parse_sql
from pglast import ast
from sqlalchemy import text

from src.database import engine


def validate_query(query):
    clean_query = query.strip()

    if not clean_query:
        raise ValueError("Query cannot be empty.")

    try:
        statements = parse_sql(clean_query)
    except Exception as error:
        raise ValueError("Invalid SQL query.") from error

    if len(statements) != 1:
        raise ValueError("Only one SQL statement is allowed.")

    statement = statements[0].stmt

    if not isinstance(statement, ast.SelectStmt):
        raise ValueError("Only SELECT queries are allowed.")

    def check_select(node):
        if not isinstance(node, ast.SelectStmt):
            raise ValueError("Only SELECT queries are allowed.")

        if node.intoClause is not None:
            raise ValueError("SELECT INTO is not allowed.")

        if node.lockingClause:
            raise ValueError("Locking clauses are not allowed.")

        if node.withClause:
            for cte in node.withClause.ctes:
                check_select(cte.ctequery)

    check_select(statement)

    return clean_query


def query_database(query):
    clean_query = validate_query(query)

    with engine.connect() as connection:
        with connection.begin():
            connection.execute(
                text("SET TRANSACTION READ ONLY")
            )
            connection.execute(
                text("SET LOCAL statement_timeout = '15s'")
            )
            result = pd.read_sql(
                text(clean_query),
                connection
            )

    return result
