import os
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from ...config import MCP_MODEL
from . import prompt

# Load environment variables
load_dotenv()
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")

trading_analyst_agent = Agent(
    model=MCP_MODEL,
    name="trading_analyst_agent",
    instruction=prompt.TRADING_ANALYST_PROMPT,
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="alphavantage-mcp",
                    args=[],
                    env={
                        **os.environ.copy(),
                        "ALPHAVANTAGE_API_KEY": ALPHA_VANTAGE_KEY,
                    }
                )
            )
        )
    ],
    output_key="proposed_trading_strategies_output",
)