import os
from dotenv import load_dotenv
from google.adk import Agent  # Or LlmAgent based on your preference
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
                    command="uvx",
                    args=[
                        "av-mcp",
                        ALPHA_VANTAGE_KEY
                    ],
                    env=os.environ.copy()
                )
            )
        )
    ],
    output_key="proposed_trading_strategies_output",
)