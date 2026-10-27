
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]


async def call_mcp_tool_async(
    tool_name: str,
    arguments: dict | None = None
):
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp_server.server"],
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                tool_name,
                arguments=arguments or {}
            )

            if result.isError:
                raise ValueError("MCP tool execution failed.")

            if result.structuredContent is not None:
                return result.structuredContent

            if not result.content:
                raise ValueError("MCP returned an empty response.")

            text_blocks = [
                block.text
                for block in result.content
                if block.type == "text"
            ]

            if not text_blocks:
                raise ValueError("MCP returned no text content.")

            return json.loads(text_blocks[0])


def call_mcp_tool(
    tool_name: str,
    arguments: dict | None = None
):
    return asyncio.run(
        call_mcp_tool_async(tool_name, arguments)
    )
