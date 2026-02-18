import os
from dotenv import load_dotenv
from google.adk import Agent  # Or LlmAgent based on your preference
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.tools import google_search
from . import prompt

from ...config import MCP_MODEL
load_dotenv()
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")

data_analyst_agent = Agent(
    model=MCP_MODEL,
    name="data_analyst_agent",
    instruction=prompt.DATA_ANALYST_PROMPT,
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="uvx",
                    args=["av-mcp", ALPHAVANTAGE_API_KEY],
                    env=os.environ.copy(),
                )
            )
        )
    ],
    output_key="proposed_trading_strategies_output",
)