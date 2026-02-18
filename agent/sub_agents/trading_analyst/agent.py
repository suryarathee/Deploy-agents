import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from ...config import MCP_MODEL
from . import prompt

# Load .env using an explicit path anchored to this file's location,
# so it works regardless of the working directory when the module is imported.
_env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

# Support both ALPHAVANTAGE_API_KEY and ALPHA_VANTAGE_KEY names
_api_key = os.getenv("ALPHAVANTAGE_API_KEY") or os.getenv("ALPHA_VANTAGE_KEY") or ""
if not _api_key:
    raise RuntimeError(
        "ALPHAVANTAGE_API_KEY is not set. "
        "Add it to your .env file or environment before starting the server."
    )



trading_analyst_agent = Agent(
    model=MCP_MODEL,
    name="trading_analyst_agent",
    instruction=prompt.TRADING_ANALYST_PROMPT,
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="uvx",
                    args=["av-mcp", _api_key],
                    env=os.environ.copy(),
                )
            )
        )
    ],
    output_key="proposed_trading_strategies_output",
)