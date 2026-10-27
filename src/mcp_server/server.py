
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from sqlalchemy import inspect

from src.database import engine
from src.tools.query_database import query_database


load_dotenv()


mcp = FastMCP("AI Data Analyst PostgreSQL")


@mcp.tool()
def inspect_database_schema() -> dict:
    inspector = inspect(engine)

    allowed_tables = {
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

    schema = {}

    for table_name in sorted(allowed_tables):
        columns = inspector.get_columns(
            table_name,
            schema="public"
        )

        foreign_keys = inspector.get_foreign_keys(
            table_name,
            schema="public"
        )

        schema[table_name] = {
            "columns": [
                {
                    "name": column["name"],
                    "type": str(column["type"]),
                    "nullable": column["nullable"]
                }
                for column in columns
            ],
            "foreign_keys": [
                {
                    "columns": fk["constrained_columns"],
                    "referenced_table": fk["referred_table"],
                    "referenced_columns": fk["referred_columns"]
                }
                for fk in foreign_keys
            ]
        }

    return schema


@mcp.tool()
def execute_database_query(query: str) -> dict:
    dataframe = query_database(query)

    return {
        "columns": dataframe.columns.tolist(),
        "rows": dataframe.astype(object).where(
            dataframe.notna(), None
        ).to_dict(orient="records"),
        "row_count": len(dataframe)
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
