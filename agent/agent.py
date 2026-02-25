"""Financial coordinator: provide reasonable investment strategies"""

from contextlib import AsyncExitStack

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from . import prompt
from .sub_agents.data_analyst import create_data_analyst_agent
from .sub_agents.execution_analyst import execution_analyst_agent
from .sub_agents.risk_analyst import risk_analyst_agent
from .sub_agents.trading_analyst import create_trading_analyst_agent

from .config import MODEL


async def create_root_agent():
    """
    Build the full financial_coordinator agent tree with live MCP sessions.

    Returns (root_agent, exit_stack).
    The caller MUST call `await exit_stack.aclose()` when the run is complete
    so that all MCP subprocess connections are cleanly shut down.
    """
    stack = AsyncExitStack()

    # Create MCP-backed sub-agents; each returns (agent, its_own_exit_stack).
    # Nest each sub-agent's exit stack inside our combined stack so a single
    # `await stack.aclose()` call tears down all MCP sessions safely.
    data_agent, data_exit = await create_data_analyst_agent()
    stack.push_async_callback(data_exit.aclose)

    trading_agent, trading_exit = await create_trading_analyst_agent()
    stack.push_async_callback(trading_exit.aclose)

    financial_coordinator = LlmAgent(
        name="financial_coordinator",
        model=MODEL,
        description=(
            "guide users through a structured process to receive financial "
            "advice by orchestrating a series of expert subagents. help them "
            "analyze a market ticker, develop trading strategies, define "
            "execution plans, and evaluate the overall risk."
        ),
        instruction=prompt.FINANCIAL_COORDINATOR_PROMPT,
        output_key="financial_coordinator_output",
        tools=[
            AgentTool(agent=data_agent),
            AgentTool(agent=trading_agent),
            AgentTool(agent=execution_analyst_agent),
            AgentTool(agent=risk_analyst_agent),
        ],
    )

    return financial_coordinator, stack