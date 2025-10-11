# main.py - FastAPI Task Manager
# This file should be in: C:\Users\rathe\Desktop\Deploy Agents\main.py
# Run with: uvicorn main:app --host 0.0.0.0 --port 8082 --reload

import uuid
import threading
import requests
from fastapi import FastAPI, BackgroundTasks

# ✅ ADK server endpoint (make sure ADK is running with: adk api_server --port 8085)
ADK_AGENT_URL = "http://localhost:8085"

app = FastAPI()
task_results = {}
task_lock = threading.Lock()


def long_running_agent_task(task_id: str, payload: dict):
    """
    Execute an agent run using the correct ADK API flow:
    1. Create/update session with POST to session endpoint
    2. Run agent with POST to /run endpoint
    """
    print(f"[TASK STARTED] {task_id}")
    try:
        # Extract parameters
        app_name = payload.get("appName", "agent")  # ✅ Changed to "agent"
        user_id = payload.get("userId")
        session_id = payload.get("sessionId")
        new_message = payload.get("newMessage")

        # ✅ STEP 1: Create/initialize session (optional but recommended)
        session_endpoint = f"{ADK_AGENT_URL}/apps/{app_name}/users/{user_id}/sessions/{session_id}"

        session_payload = {
            "state": {}  # Initialize with empty state or any initial state
        }

        print(f"[INITIALIZING SESSION] {session_endpoint}")
        session_response = requests.post(
            session_endpoint,
            json=session_payload,
            timeout=10
        )

        if session_response.status_code in [200, 201]:
            print(f"[SESSION INITIALIZED] {session_id}")
        else:
            print(f"[SESSION RESPONSE] {session_response.status_code}: {session_response.text[:200]}")

        # ✅ STEP 2: Run the agent with /run endpoint
        run_endpoint = f"{ADK_AGENT_URL}/run"

        # Build payload with snake_case as per ADK docs
        run_payload = {
            "app_name": app_name,
            "user_id": user_id,
            "session_id": session_id,
            "new_message": new_message
        }

        print(f"[RUNNING AGENT] {run_endpoint}")
        print(f"[RUN PAYLOAD] {run_payload}")

        # The /run endpoint returns all events when complete
        run_response = requests.post(
            run_endpoint,
            json=run_payload,
            timeout=300  # 5 minutes timeout for agent processing
        )

        print(f"[RUN RESPONSE STATUS] {run_response.status_code}")
        run_response.raise_for_status()

        # Response is a JSON array of Event objects
        events = run_response.json()
        print(f"[RECEIVED {len(events)} EVENTS]")

        # Extract the final agent response from events
        agent_response = None
        agent_message = None

        for event in reversed(events):  # Check newest first
            # Look for content in the event
            if event.get('content'):
                content = event['content']
                # Extract text from parts if available
                if content.get('parts'):
                    for part in content['parts']:
                        if part.get('text'):
                            agent_message = part['text']
                            break
                if agent_message:
                    agent_response = event
                    break

        with task_lock:
            task_results[task_id] = {
                "status": "SUCCESS",
                "result": {
                    "message": agent_message,
                    "response": agent_response,
                    "all_events": events,
                    "session_id": session_id,
                    "user_id": user_id
                }
            }
        print(f"[TASK COMPLETED] {task_id}")
        if agent_message:
            print(f"[AGENT MESSAGE] {agent_message[:200]}...")

    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
        with task_lock:
            task_results[task_id] = {"status": "FAILURE", "result": error_msg}
        print(f"[TASK FAILED] {task_id} → {error_msg}")
    except requests.exceptions.Timeout:
        with task_lock:
            task_results[task_id] = {"status": "TIMEOUT", "result": "Agent run exceeded timeout"}
        print(f"[TASK TIMEOUT] {task_id}")
    except Exception as e:
        with task_lock:
            task_results[task_id] = {"status": "FAILURE", "result": str(e)}
        print(f"[TASK FAILED] {task_id} → {e}")


@app.post("/run-async")
def start_task(payload: dict, background_tasks: BackgroundTasks):
    """
    Start an async agent run task.
    Returns a task_id to check status later.
    """
    task_id = str(uuid.uuid4())

    # Generate a unique session ID if missing
    if "sessionId" not in payload or not payload["sessionId"]:
        payload["sessionId"] = str(uuid.uuid4())

    # Generate user ID if missing
    if "userId" not in payload or not payload["userId"]:
        payload["userId"] = str(uuid.uuid4())

    with task_lock:
        task_results[task_id] = {"status": "PENDING", "result": None}

    background_tasks.add_task(long_running_agent_task, task_id, payload)
    return {"task_id": task_id, "session_id": payload["sessionId"], "user_id": payload["userId"]}


@app.get("/task-status/{task_id}")
def get_task_status(task_id: str):
    """
    Get the status of a running task.
    Returns: {"status": "PENDING|SUCCESS|FAILURE|TIMEOUT", "result": ...}
    """
    with task_lock:
        result = task_results.get(task_id, {"status": "NOT_FOUND", "result": None})
    return result


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ADK Task Manager"}