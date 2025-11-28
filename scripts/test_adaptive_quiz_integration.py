#!/usr/bin/env python3
"""
Integration test for the Adaptive Quiz Master agent.

Usage:
  python scripts/test_adaptive_quiz_integration.py

Environment variables (optional):
  SUPERVISOR_URL  (default: http://localhost:8000)
  AQ_AGENT_URL    (default: http://localhost:5020)
  EMAIL           (default: test@example.com)
  PASSWORD        (default: password)
"""

import os
import sys
import json
from pprint import pprint

try:
    import requests
except Exception as e:
    print("The `requests` library is required. Install with: pip install requests")
    sys.exit(2)

SUPERVISOR = os.getenv("SUPERVISOR_URL", "http://localhost:8000")
AQ_AGENT = os.getenv("AQ_AGENT_URL", "http://localhost:5020")
EMAIL = os.getenv("EMAIL", "test@example.com")
PASSWORD = os.getenv("PASSWORD", "password")

TIMEOUT = 10

TEST_QUERY = "Generate a 10-question adaptive multiple-choice quiz on Python basics (loops and functions) at medium difficulty."


def check_health(url, name):
    health_url = url.rstrip("/") + "/health"
    print(f"Checking {name} health: {health_url}")
    try:
        r = requests.get(health_url, timeout=TIMEOUT)
        print(f"  status_code: {r.status_code}")
        try:
            pprint(r.json())
        except Exception:
            print("  (non-json body):", r.text[:500])
        return r.status_code == 200
    except Exception as e:
        print(f"  ERROR contacting {name}: {e}")
        return False


def login_supervisor():
    url = SUPERVISOR.rstrip("/") + "/api/auth/login"
    print(f"Logging into supervisor at {url} as {EMAIL}")
    payload = {"email": EMAIL, "password": PASSWORD}
    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT)
    except Exception as e:
        print(f"  ERROR contacting supervisor login: {e}")
        return None
    if r.status_code != 200:
        print(f"  Login failed: status={r.status_code} body={r.text}")
        return None
    try:
        body = r.json()
        token = body.get("token")
        user = body.get("user")
        print("  Login succeeded. User:")
        pprint(user)
        return token
    except Exception as e:
        print(f"  Could not parse login response: {e}")
        return None


def identify_intent(token, query):
    url = SUPERVISOR.rstrip("/") + "/api/supervisor/identify-intent"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"query": query}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
    except Exception as e:
        print(f"  ERROR contacting identify-intent: {e}")
        return None
    try:
        return r.json()
    except Exception:
        print("  identify-intent returned non-json:", r.text[:1000])
        return None


def submit_direct_agent_task():
    url = AQ_AGENT.rstrip("/") + "/process"
    headers = {"Content-Type": "application/json"}

    task_envelope = {
        "message_id": "msg-test-1",
        "sender": "test-script",
        "recipient": "adaptive_quiz_master_agent",
        "task": {
            "name": "generate_adaptive_quiz",
            "parameters": {
                "agent_name": "adaptive_quiz_master_agent",
                "intent": "generate_adaptive_quiz",
                "payload": {
                    "user_info": {"user_id": "user123", "learning_level": "intermediate"},
                    "quiz_request": {
                        "topic": "Python basics (loops and functions)",
                        "num_questions": 10,
                        "question_types": ["mcq"],
                        "bloom_taxonomy_level": "apply",
                        "adaptive": True
                    },
                    "session_info": {"session_id": "sess-1"}
                }
            }
        }
    }

    print(f"Sending direct TaskEnvelope to adaptive quiz agent: {url}")
    try:
        r = requests.post(url, json=task_envelope, headers=headers, timeout=30)
    except Exception as e:
        print(f"  ERROR sending to agent: {e}")
        return None, None
    print(f"  status={r.status_code}")
    try:
        body = r.json()
        print("Agent response:")
        pprint(body)
        return r.status_code, body
    except Exception:
        print("Non-JSON response from agent:", r.text[:1000])
        return r.status_code, None


def submit_supervisor_request(token, text, explicit_agent=False):
    url = SUPERVISOR.rstrip("/") + "/api/supervisor/request"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "request": text,
        "autoRoute": not explicit_agent,
        "includeHistory": False
    }
    if explicit_agent:
        payload["agentId"] = "adaptive_quiz_master_agent"

    print(f"Submitting request to supervisor: {text} (explicit_agent={explicit_agent})")
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
    except Exception as e:
        print(f"  ERROR sending request to supervisor: {e}")
        return None, None
    print(f"  status={r.status_code}")
    try:
        body = r.json()
        print("Supervisor response:")
        pprint(body)
        return r.status_code, body
    except Exception:
        print("Non-JSON response:", r.text[:1000])
        return r.status_code, None


if __name__ == '__main__':
    print("\n=== Adaptive Quiz Agent integration test ===")

    agent_ok = check_health(AQ_AGENT, "adaptive_quiz_master_agent")
    if not agent_ok:
        print("Adaptive quiz agent health check failed. Please start the agent (or check Docker).")

    token = login_supervisor()
    if not token:
        print("Supervisor login failed; cannot run supervisor-backed tests.")

    # 1) Test identify-intent via supervisor
    if token:
        print("\n-- identify-intent test --")
        intent_result = identify_intent(token, TEST_QUERY)
        if intent_result:
            got = intent_result.get("agent_id") or intent_result.get("agentId")
            print(f"Identified agent: {got}")
            if got == "adaptive_quiz_master_agent":
                print("IDENTIFY-INTENT PASS: adaptive_quiz_master_agent")
            else:
                print("IDENTIFY-INTENT FAIL: expected adaptive_quiz_master_agent")

    # 2) Send direct TaskEnvelope to the agent (should succeed)
    print("\n-- direct agent TaskEnvelope test --")
    status, body = submit_direct_agent_task()
    if status == 200 and body and isinstance(body, dict) and body.get("status") == "SUCCESS":
        print("DIRECT AGENT TEST PASS: agent returned SUCCESS")
    else:
        print("DIRECT AGENT TEST FAIL: agent did not return SUCCESS")

    # 3) Submit supervisor request (explicit agent override) to replicate earlier missing-fields behavior
    if token:
        print("\n-- supervisor forward (explicit agent) test --")
        s_status, s_body = submit_supervisor_request(token, TEST_QUERY, explicit_agent=True)
        if s_body and isinstance(s_body, dict):
            # Look for error message indicating missing required fields
            msg = s_body.get("response") or (s_body.get("error") or {}).get("message") or str(s_body)
            if "Missing required fields" in json.dumps(s_body) or (msg and "Missing required fields" in str(msg)):
                print("SUPERVISOR FORWARD TEST: observed missing required fields (as expected without structured payload)")
            else:
                print("SUPERVISOR FORWARD TEST: supervisor returned:")
                pprint(s_body)

    print("\nDone.")
