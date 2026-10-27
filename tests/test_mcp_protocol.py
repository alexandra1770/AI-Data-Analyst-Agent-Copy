
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_mcp_protocol_lists_tools():
    project_root = Path(__file__).resolve().parents[1]

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp_server.server"],
        cwd=str(project_root),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            response = await session.list_tools()
            tool_names = {tool.name for tool in response.tools}

            assert "inspect_database_schema" in tool_names
            assert "execute_database_query" in tool_names


@pytest.mark.asyncio
async def test_mcp_protocol_executes_sql():
    project_root = Path(__file__).resolve().parents[1]

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp_server.server"],
        cwd=str(project_root),
    )

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


@pytest.mark.asyncio
async def test_mcp_protocol_rejects_unsafe_sql():
    project_root = Path(__file__).resolve().parents[1]

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp_server.server"],
        cwd=str(project_root),
    )

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
