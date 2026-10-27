
import pandas as pd
from pglast import parse_sql, ast
from sqlalchemy import text

from src.database import engine


ALLOWED_TABLES = {
    "category_translation",
    "customers",
    "geolocation",
    "order_items",
    "orders",
    "payments",
    "products",
    "reviews",
    "sellers",
}

# Functii PostgreSQL permise pentru analize
ALLOWED_FUNCTIONS = {
    "count",
    "sum",
    "avg",
    "min",
    "max",
    "round",
    "coalesce",
    "nullif",
    "abs",
    "sqrt",
    "power",
    "lower",
    "upper",
    "length",
    "trim",
    "ltrim",
    "rtrim",
    "substring",
    "substr",
    "replace",
    "concat",
    "concat_ws",
    "left",
    "right",
    "split_part",
    "date_trunc",
    "date_part",
    "extract",
    "to_char",
    "to_date",
    "to_timestamp",
    "now",
    "current_date",
    "greatest",
    "least",
    "string_agg",
    "array_agg",
    "bool_and",
    "bool_or",
    "stddev",
    "stddev_pop",
    "stddev_samp",
    "variance",
    "var_pop",
    "var_samp",
    "percentile_cont",
    "percentile_disc",
    "row_number",
    "rank",
    "dense_rank",
    "lag",
    "lead",
    "first_value",
    "last_value",
    "ntile",
    "generate_series",
}


def walk_ast(node):
    # Parcurge recursiv structura SQL
    if node is None:
        return

    if isinstance(node, (list, tuple)):
        for item in node:
            yield from walk_ast(item)
        return

    if not isinstance(node, ast.Node):
        return

    yield node

    for field in node:
        yield from walk_ast(getattr(node, field))


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

    # Verifica toate subinterogarile si CTE-urile
    for node in walk_ast(statement):
        if isinstance(node, ast.SelectStmt):
            if node.intoClause is not None:
                raise ValueError("SELECT INTO is not allowed.")

            if node.lockingClause:
                raise ValueError("Locking clauses are not allowed.")

        # Blocheaza operatiile SQL care modifica datele
        if isinstance(
            node,
            (
                ast.InsertStmt,
                ast.UpdateStmt,
                ast.DeleteStmt,
                ast.CreateStmt,
                ast.DropStmt,
                ast.AlterTableStmt,
            ),
        ):
            raise ValueError("Data modification is not allowed.")

        # Verifica functiile apelate
        if isinstance(node, ast.FuncCall):
            parts = [
                part.sval.lower()
                for part in node.funcname
            ]

            if len(parts) != 1 or parts[0] not in ALLOWED_FUNCTIONS:
                raise ValueError(
                    f"SQL function not allowed: {'.'.join(parts)}"
                )

    # Identifica numele CTE-urilor
    cte_names = set()

    for node in walk_ast(statement):
        if isinstance(node, ast.CommonTableExpr):
            cte_names.add(node.ctename.lower())

    # Verifica toate tabelele utilizate
    for node in walk_ast(statement):
        if isinstance(node, ast.RangeVar):
            table_name = node.relname.lower()

            if node.schemaname not in (None, "public"):
                raise ValueError(
                    f"SQL schema not allowed: {node.schemaname}"
                )

            if (
                table_name not in ALLOWED_TABLES
                and table_name not in cte_names
            ):
                raise ValueError(
                    f"Table not allowed: {table_name}"
                )

    return clean_query


def query_database(query):
    clean_query = validate_query(query)

    with engine.connect() as connection:
        with connection.begin():
            # Tranzactie doar pentru citire
            connection.execute(
                text("SET TRANSACTION READ ONLY")
            )

            # Limita de executie: 15 secunde
            connection.execute(
                text("SET LOCAL statement_timeout = '15s'")
            )

            result = pd.read_sql(
                text(clean_query),
                connection
            )

    return result
