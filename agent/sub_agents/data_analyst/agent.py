import os
from dotenv import load_dotenv
from google.adk import Agent  # Or LlmAgent based on your preference
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from . import prompt

from ...config import MODEL
# Load environment variables
load_dotenv()
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")

data_analyst_agent = Agent(
    model=MODEL,
    name="data_analyst_agent",
    instruction=prompt.DATA_ANALYST_PROMPT,
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="uvx",  # Use uvx instead of npx
                    args=[
                        "av-mcp",  # This is the Alpha Vantage python-based MCP package
                        os.getenv("ALPHA_VANTAGE_KEY")
                    ],
                    env=os.environ.copy()
                )
            )
        )
    ],
    output_key="proposed_trading_strategies_output",
)