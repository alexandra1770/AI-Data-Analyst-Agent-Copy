#inspecting database schema

from sqlalchemy import inspect

from src.database import engine


def inspect_schema():
    inspector = inspect(engine)

    schema = {}

    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        primary_key = inspector.get_pk_constraint(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)

        schema[table_name] = {
            "columns": [
                {
                    "name": column["name"],
                    "type": str(column["type"]),
                    "nullable": column["nullable"]
                }
                for column in columns
            ],
            "primary_key": primary_key.get("constrained_columns", []),
            "foreign_keys": [
                {
                    "columns": foreign_key["constrained_columns"],
                    "referenced_table": foreign_key["referred_table"],
                    "referenced_columns": foreign_key["referred_columns"]
                }
                for foreign_key in foreign_keys
            ]
        }

    return schema