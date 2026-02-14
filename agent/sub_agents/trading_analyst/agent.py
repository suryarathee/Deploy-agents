import os
from dotenv import load_dotenv
from google.adk import Agent  # Or LlmAgent based on your preference
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from ...config import MODEL
from . import prompt

# Load environment variables
load_dotenv()
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")

trading_analyst_agent = Agent(
    model=MODEL,
    name="trading_analyst_agent",
    instruction=prompt.TRADING_ANALYST_PROMPT,
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=[
                        "-y",
                        "@alphavantage/mcp-server"
                    ],
                    # IMPORTANT: Alpha Vantage requires the API key in the environment
                    env={
                        "PATH": os.environ.get("PATH", ""), # Required for npx to find node
                        "ALPHA_VANTAGE_API_KEY": ALPHA_VANTAGE_KEY
                    }
                )
            )
        )
    ],
    output_key="proposed_trading_strategies_output",
)