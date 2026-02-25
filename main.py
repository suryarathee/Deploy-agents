# main.py - FastAPI Task Manager using ADK SDK directly (no separate adk api_server needed)
# Run with: uvicorn main:app --host 0.0.0.0 --port 8082

import uuid
import asyncio
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent.agent import create_root_agent

# ── App setup ────────────────────────────────────────────────────────────────

APP_NAME = "financial_coordinator"

session_service = InMemorySessionService()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

task_results: dict = {}


# ── Request model ─────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    newMessage: str
    userId: Optional[str] = None
    sessionId: Optional[str] = None


# ── Background task ───────────────────────────────────────────────────────────

async def run_agent_async(task_id: str, payload: AgentRequest):
    """Run the ADK agent in-process using the Runner SDK."""
    print(f"[TASK STARTED] {task_id}")

    user_id = payload.userId
    session_id = payload.sessionId
    new_message = payload.newMessage

    # Build a fresh agent tree (including live MCP sessions) for this run.
    # Using an async exit stack ensures MCP subprocess connections are always
    # cleanly shut down, even if an exception occurs mid-run.
    root_agent, exit_stack = await create_root_agent()

    try:
        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service,
        )

        # Create session if it doesn't exist
        existing = await session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        if existing is None:
            await session_service.create_session(
                app_name=APP_NAME, user_id=user_id, session_id=session_id
            )

        # Build the message content
        content = types.Content(
            role="user",
            parts=[types.Part(text=new_message)]
        )

        # Run the agent and collect events
        agent_message = None

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            agent_message = part.text
                            break

        task_results[task_id] = {
            "status": "SUCCESS",
            "result": {
                "message": agent_message,
                "session_id": session_id,
                "user_id": user_id,
            }
        }
        print(f"[TASK COMPLETED] {task_id}")

    except Exception as e:
        task_results[task_id] = {"status": "FAILURE", "result": str(e)}
        print(f"[TASK FAILED] {task_id} → {e}")

    finally:
        # Always close MCP subprocess connections
        await exit_stack.aclose()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/chat")
async def start_task(payload: AgentRequest):
    """Start an async agent run task."""
    task_id = str(uuid.uuid4())

    if not payload.sessionId:
        payload.sessionId = str(uuid.uuid4())
    if not payload.userId:
        payload.userId = str(uuid.uuid4())

    task_results[task_id] = {"status": "PENDING", "result": None}

    # Use asyncio.create_task so the MCP subprocess runs on the main event loop.
    # This is required — StdioConnectionParams breaks when run in a new thread's loop.
    asyncio.create_task(run_agent_async(task_id, payload))

    return {
        "task_id": task_id,
        "session_id": payload.sessionId,
        "user_id": payload.userId,
        "status": "PENDING"
    }


@app.get("/task/{task_id}")
def get_task_status(task_id: str):
    """Get the status of a running task."""
    result = task_results.get(task_id)

    if not result:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "status": result["status"],
        "result": result["result"]
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ADK Financial Coordinator"}