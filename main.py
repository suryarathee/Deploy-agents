# main.py - FastAPI Task Manager (Simple In-Memory Version)
# Run with: uvicorn main:app --host 0.0.0.0 --port 8082 --reload

import uuid
import threading
import requests
import os
import json
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional

# ✅ CONFIGURATION
# Uses environment variable for Docker, defaults to localhost for local testing
ADK_AGENT_URL = os.getenv("ADK_AGENT_URL", "http://localhost:8085")

app = FastAPI()

# ✅ Simple In-Memory Storage (from your original file)
task_results = {}
task_lock = threading.Lock()


# ✅ Pydantic Model for Input Validation
class AgentRequest(BaseModel):
    newMessage: str
    userId: Optional[str] = None
    sessionId: Optional[str] = None
    appName: str = "agent"


def long_running_agent_task(task_id: str, payload: AgentRequest):
    """
    Execute an agent run using the correct ADK API flow.
    """
    print(f"[TASK STARTED] {task_id}")
    print(f"[WORKER] Connecting to ADK at: {ADK_AGENT_URL}")

    try:
        # Extract parameters
        app_name = payload.appName
        user_id = payload.userId
        session_id = payload.sessionId
        new_message = payload.newMessage

        # ✅ STEP 1: Create/initialize session
        session_endpoint = f"{ADK_AGENT_URL}/apps/{app_name}/users/{user_id}/sessions/{session_id}"

        # Try to initialize session (ignore if already exists)
        try:
            requests.post(session_endpoint, json={"state": {}}, timeout=5)
        except Exception as e:
            print(f"[WARNING] Session init minor error: {e}")

        # ✅ STEP 2: Run the agent with /run endpoint
        # FIX: Format the message as a proper 'Turn' object for ADK
        formatted_message = {
            "role": "user",
            "parts": [{"text": new_message}]
        }

        run_endpoint = f"{ADK_AGENT_URL}/run"
        run_payload = {
            "app_name": app_name,
            "user_id": user_id,
            "session_id": session_id,
            "new_message": formatted_message  # <-- Sending the object, not just string
        }

        print(f"[RUNNING AGENT] {run_endpoint}")

        run_response = requests.post(
            run_endpoint,
            json=run_payload,
            timeout=300
        )

        # Debugging helper for 422 errors
        if run_response.status_code == 422:
            print(f"[ADK ERROR 422] Response: {run_response.text}")

        run_response.raise_for_status()

        # Response is a JSON array of Event objects
        events = run_response.json()
        print(f"[RECEIVED {len(events)} EVENTS]")

        # Extract the final agent response
        agent_message = None

        for event in reversed(events):
            if event.get('content') and event['content'].get('parts'):
                for part in event['content']['parts']:
                    if part.get('text'):
                        agent_message = part['text']
                        break
            if agent_message:
                break

        # Save result to memory
        with task_lock:
            task_results[task_id] = {
                "status": "SUCCESS",
                "result": {
                    "message": agent_message,
                    "all_events": events,
                    "session_id": session_id,
                    "user_id": user_id
                }
            }
        print(f"[TASK COMPLETED] {task_id}")

    except requests.exceptions.Timeout:
        with task_lock:
            task_results[task_id] = {"status": "TIMEOUT", "result": "Agent run exceeded timeout"}
        print(f"[TASK TIMEOUT] {task_id}")
    except Exception as e:
        with task_lock:
            task_results[task_id] = {"status": "FAILURE", "result": str(e)}
        print(f"[TASK FAILED] {task_id} → {e}")


@app.post("/chat")
def start_task(payload: AgentRequest, background_tasks: BackgroundTasks):
    """
    Start an async agent run task.
    """
    task_id = str(uuid.uuid4())

    # Generate IDs if missing
    if not payload.sessionId:
        payload.sessionId = str(uuid.uuid4())
    if not payload.userId:
        payload.userId = str(uuid.uuid4())

    with task_lock:
        task_results[task_id] = {"status": "PENDING", "result": None}

    background_tasks.add_task(long_running_agent_task, task_id, payload)

    return {
        "task_id": task_id,
        "session_id": payload.sessionId,
        "user_id": payload.userId,
        "status": "PENDING"
    }


@app.get("/task/{task_id}")
def get_task_status(task_id: str):
    """
    Get the status of a running task.
    """
    with task_lock:
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
    return {"status": "healthy", "service": "ADK Task Manager"}