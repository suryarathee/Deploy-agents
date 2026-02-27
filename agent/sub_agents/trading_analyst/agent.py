import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.mcp_tool import MCPToolset
from mcp import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams

from ...config import MCP_MODEL
from . import prompt

_env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

_api_key = os.getenv("ALPHAVANTAGE_API_KEY") or os.getenv("ALPHA_VANTAGE_KEY") or ""
if not _api_key:
    raise RuntimeError(
        "ALPHAVANTAGE_API_KEY is not set. "
        "Add it to your .env file or environment before starting the server."
    )

mcp_tools = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="uvx",
            args=["av-mcp", _api_key],
            env=os.environ.copy(),
        ),
        timeout=300.0
    )
)

trading_analyst_agent = Agent(
    model=MCP_MODEL,
    name="trading_analyst_agent",
    instruction=prompt.TRADING_ANALYST_PROMPT,
    tools=[mcp_tools],
    output_key="proposed_trading_strategies_output",
)