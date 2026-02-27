import os
from contextlib import AsyncExitStack
from pathlib import Path
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.mcp_tool import MCPToolset
from mcp import StdioServerParameters
from . import prompt

from ...config import MCP_MODEL

_env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

# Support both ALPHAVANTAGE_API_KEY and ALPHA_VANTAGE_KEY names
_api_key = os.getenv("ALPHAVANTAGE_API_KEY") or os.getenv("ALPHA_VANTAGE_KEY") or ""
if not _api_key:
    raise RuntimeError(
        "ALPHAVANTAGE_API_KEY is not set. "
        "Add it to your .env file or environment before starting the server."
    )


async def create_data_analyst_agent():
    """
    Create a fresh data_analyst_agent with a live MCP toolset.
    Returns (agent, exit_stack) — caller must close the exit_stack when done.
    """
    exit_stack = AsyncExitStack()
    mcp_tools = await exit_stack.enter_async_context(
        MCPToolset(
            connection_params=StdioServerParameters(
                command="uvx",
                args=["av-mcp", _api_key],
                env=os.environ.copy(),
            )
        )
    )

    agent = Agent(
        model=MCP_MODEL,
        name="data_analyst_agent",
        instruction=prompt.DATA_ANALYST_PROMPT,
        tools=mcp_tools,
        output_key="proposed_trading_strategies_output",
    )
    return agent, exit_stack