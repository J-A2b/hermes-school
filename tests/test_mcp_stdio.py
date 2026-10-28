import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_real_stdio_handshake_and_call():
    async def exercise():
        params = StdioServerParameters(command=sys.executable, args=['-m', 'hermes_school.cli', 'mcp'], env=dict(os.environ))
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert len(tools.tools) == 11
                result = await session.call_tool('school_get_weekend_context', {})
                assert not result.isError
                assert result.structuredContent['timezone'] == 'Europe/Paris'
                invalid = await session.call_tool('school_update_personal_task', {'task_id': -1, 'done': True})
                assert invalid.isError
    asyncio.run(exercise())
