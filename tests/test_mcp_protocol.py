
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.getenv("RUN_MCP_INTEGRATION_TESTS") != "1",
        reason="MCP integration tests require a configured PostgreSQL database"
    )
]


def get_server_params():
    project_root = Path(__file__).resolve().parents[1]

    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp_server.server"],
        cwd=str(project_root),
    )


async def test_mcp_protocol_lists_tools():
    server_params = get_server_params()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            response = await session.list_tools()
            tool_names = {tool.name for tool in response.tools}

            assert "inspect_database_schema" in tool_names
            assert "execute_database_query" in tool_names


async def test_mcp_protocol_executes_sql():
    server_params = get_server_params()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            response = await session.call_tool(
                "execute_database_query",
                arguments={
                    "query": "SELECT COUNT(*) AS total_orders FROM orders"
                },
            )

            assert not response.isError
            assert response.content


async def test_mcp_protocol_rejects_unsafe_sql():
    server_params = get_server_params()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            response = await session.call_tool(
                "execute_database_query",
                arguments={
                    "query": "DELETE FROM orders"
                },
            )

            assert response.isError
