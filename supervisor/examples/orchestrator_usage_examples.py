# supervisor/examples/orchestrator_usage_examples.py
"""
Comprehensive examples of using the Unified Gemini Chat Orchestrator.

These examples demonstrate:
1. Direct orchestrator usage (Python)
2. HTTP API usage (cURL and JavaScript)
3. Integration with existing code
4. Multi-turn conversations
5. Error handling
6. Custom configurations
"""

import asyncio
import logging
from supervisor.gemini_chat_orchestrator import (
    create_orchestrator,
    get_orchestrator,
    reset_orchestrator
)

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


# =============================================================================
# Example 1: Direct Orchestrator Usage (Python)
# =============================================================================

async def example_1_direct_usage():
    """Example: Using orchestrator directly in Python code."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Direct Orchestrator Usage")
    print("="*60)
    
    # Create a fresh orchestrator
    reset_orchestrator()
    orchestrator = get_orchestrator()
    
    # Example 1a: Clear request (no clarification needed)
    print("\n1a. Clear Quiz Request:")
    user_message = "Create me a 10-question Python quiz at beginner level"
    print(f"User: {user_message}")
    
    # In real code, this would be: await orchestrator.process_message(user_message)
    # For this example, we'll just show the structure
    print("Orchestrator will:")
    print("  1. Build system prompt with all agent definitions")
    print("  2. Call Gemini with the user message")
    print("  3. Parse JSON response")
    print("  4. Return GeminiChatOrchestratorResponse")
    
    print("\nExpected response:")
    print({
        "status": "READY_TO_ROUTE",
        "agent_id": "adaptive_quiz_master_agent",
        "confidence": 0.95,
        "reasoning": "Clear intent to create a quiz on Python",
        "extracted_params": {
            "topic": "Python",
            "num_questions": 10,
            "difficulty": "beginner"
        },
        "clarifying_questions": [],
        "agent_payload": {
            "request": "Create me a 10-question Python quiz at beginner level",
            "topic": "Python",
            "num_questions": 10,
            "difficulty": "beginner"
        }
    })
    
    # Example 1b: Ambiguous request (needs clarification)
    print("\n\n1b. Ambiguous Request:")
    user_message = "I need help"
    print(f"User: {user_message}")
    
    print("\nExpected response:")
    print({
        "status": "CLARIFICATION_NEEDED",
        "agent_id": None,
        "confidence": 0.25,
        "reasoning": "Too vague - could be any type of help",
        "extracted_params": {},
        "clarifying_questions": [
            "What subject are you studying?",
            "What specific help do you need?"
        ]
    })
    
    # Example 1c: Multi-turn conversation
    print("\n\n1c. Multi-turn Conversation:")
    print("\nTurn 1:")
    user_message = "I need help"
    print(f"User: {user_message}")
    print("Assistant: What subject are you studying? What specific help do you need?")
    
    print("\nTurn 2:")
    user_message = "I have a Python assignment on sorting algorithms"
    print(f"User: {user_message}")
    print("Orchestrator remembers context from turn 1")
    
    print("\nExpected response:")
    print({
        "status": "READY_TO_ROUTE",
        "agent_id": "assignment_coach_agent",
        "confidence": 0.92,
        "reasoning": "User now clarified they need assignment help on Python sorting",
        "extracted_params": {
            "task_description": "assignment on sorting algorithms",
            "subject": "Python"
        }
    })


# =============================================================================
# Example 2: Integration with FastAPI Endpoint
# =============================================================================

def example_2_fastapi_integration():
    """Example: How orchestrator integrates with FastAPI endpoint."""
    print("\n" + "="*60)
    print("EXAMPLE 2: FastAPI Integration")
    print("="*60)
    
    code = '''
# In supervisor/main.py
from supervisor.gemini_chat_orchestrator import get_orchestrator

@app.post('/api/supervisor/request-unified')
async def submit_request_unified(
    payload: EnhancedRequestPayload,
    user: User = Depends(auth.require_auth)
):
    """Unified Gemini orchestrator endpoint."""
    user_id = user.id
    user_query = payload.request
    
    # Get orchestrator
    orchestrator = get_orchestrator()
    
    # Store user message
    memory_manager.store_conversation_message(
        user_id=user_id,
        role="user",
        content=user_query
    )
    
    # Process through orchestrator
    orchestrator_response = await orchestrator.process_message(user_query)
    
    # Handle response
    if orchestrator_response.status == "READY_TO_ROUTE":
        # Forward to agent
        agent_response = await forward_to_agent(
            orchestrator_response.agent_id,
            forward_payload,
            agent_specific=orchestrator_response.agent_payload
        )
        
        # Return to client
        return {
            "status": "AGENT_RESPONSE",
            "agent_id": orchestrator_response.agent_id,
            "response": agent_response.response,
            ...
        }
    
    else:  # CLARIFICATION_NEEDED
        return {
            "status": "clarification_needed",
            "clarifying_questions": orchestrator_response.clarifying_questions,
            ...
        }
'''
    print(code)


# =============================================================================
# Example 3: HTTP API Usage
# =============================================================================

def example_3_http_api():
    """Example: Using the API via HTTP."""
    print("\n" + "="*60)
    print("EXAMPLE 3: HTTP API Usage")
    print("="*60)
    
    # cURL example
    curl_example = '''
# cURL: Clear request (no clarification)
curl -X POST http://localhost:8000/api/supervisor/request-unified \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{
    "request": "Create a 10-question Python quiz at beginner level"
  }'

Response:
{
    "status": "AGENT_RESPONSE",
    "agent_id": "adaptive_quiz_master_agent",
    "response": "[Quiz content generated by agent]",
    "confidence": 0.95,
    ...
}


# cURL: Ambiguous request (needs clarification)
curl -X POST http://localhost:8000/api/supervisor/request-unified \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{
    "request": "I need help"
  }'

Response:
{
    "status": "clarification_needed",
    "clarifying_questions": [
        "What subject are you studying?",
        "What specific help do you need?"
    ],
    ...
}
'''
    print(curl_example)
    
    # JavaScript/TypeScript example
    js_example = '''
// JavaScript/TypeScript example
async function sendRequest(message: string) {
    const response = await fetch('/api/supervisor/request-unified', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            request: message,
            includeHistory: true
        })
    });
    
    const data = await response.json();
    
    if (data.status === 'AGENT_RESPONSE') {
        // Display agent response
        showResponse(data.response, {
            agent: data.agent_name,
            confidence: data.confidence
        });
    } else if (data.status === 'clarification_needed') {
        // Ask clarifying questions
        showClarificationModal(data.clarifying_questions);
    } else if (data.status === 'ERROR') {
        // Show error
        showError(data.error);
    }
    
    return data;
}

// Usage
const result = await sendRequest("Create a Python quiz");
'''
    print(js_example)


# =============================================================================
# Example 4: All Agent Types
# =============================================================================

async def example_4_all_agent_types():
    """Example: Requests for each of the 5 agents."""
    print("\n" + "="*60)
    print("EXAMPLE 4: All Agent Types")
    print("="*60)
    
    examples = [
        {
            "name": "Adaptive Quiz Master",
            "request": "Generate 5 multiple-choice questions on machine learning at intermediate difficulty",
            "extracted_params": {
                "topic": "machine learning",
                "num_questions": 5,
                "question_type": "mcq",
                "difficulty": "intermediate"
            }
        },
        {
            "name": "Research Scout",
            "request": "Find research papers on blockchain technology from 2020 to 2023, limit to 10 results",
            "extracted_params": {
                "topic": "blockchain technology",
                "year_range": {"from": "2020", "to": "2023"},
                "max_results": 10
            }
        },
        {
            "name": "Assignment Coach",
            "request": "Help me understand photosynthesis for my biology assignment",
            "extracted_params": {
                "task_description": "Understand photosynthesis",
                "subject": "Biology"
            }
        },
        {
            "name": "Plagiarism Prevention",
            "request": 'Check this for plagiarism: "The rapid development of artificial intelligence has transformed industries worldwide"',
            "extracted_params": {
                "text_content": "The rapid development of artificial intelligence has transformed industries worldwide",
                "check_type": "check"
            }
        },
        {
            "name": "Gemini Wrapper (General)",
            "request": "What is quantum computing and why is it important?",
            "extracted_params": {}
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['name']}")
        print(f"   Request: {example['request']}")
        print(f"   Extracted: {example['extracted_params']}")


# =============================================================================
# Example 5: Conversation State Management
# =============================================================================

async def example_5_conversation_state():
    """Example: Managing conversation state across messages."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Conversation State Management")
    print("="*60)
    
    code = '''
# Create orchestrator
orchestrator = create_orchestrator()

# Turn 1: User asks vague question
message1 = "I need help"
response1 = await orchestrator.process_message(message1)
# response1.status = "CLARIFICATION_NEEDED"
# Orchestrator stores this in conversation_history

# Turn 2: User provides clarification
message2 = "I have a Python assignment"
response2 = await orchestrator.process_message(message2)
# response2.status = "READY_TO_ROUTE"
# Orchestrator remembers context from message1

# View conversation state
state = orchestrator.get_state()
print(state)
# {
#     "current_agent_id": "assignment_coach_agent",
#     "extracted_params": {"task_description": "...", "subject": "Python"},
#     "conversation_length": 2,
#     "available_agents": [...]
# }

# Get conversation history
history = orchestrator.get_conversation_history()
# Returns list of messages with roles and timestamps

# Reset for new conversation
orchestrator.reset_conversation()
# Clears history, extracted_params, current_agent_id
'''
    print(code)


# =============================================================================
# Example 6: Error Handling & Fallbacks
# =============================================================================

def example_6_error_handling():
    """Example: Error handling and fallback strategies."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Error Handling & Fallbacks")
    print("="*60)
    
    code = '''
# The orchestrator handles errors gracefully:

# 1. If Gemini API fails:
try:
    response = await orchestrator.process_message(user_message)
except Exception as e:
    # Returns CLARIFICATION_NEEDED response asking to rephrase
    return {
        "status": "CLARIFICATION_NEEDED",
        "clarifying_questions": ["Could you please rephrase your request?"]
    }

# 2. If Gemini returns invalid JSON:
response_text = "This is not JSON"
parsed = orchestrator._parse_gemini_response(response_text)
# Returns:
# {
#     "status": "CLARIFICATION_NEEDED",
#     "clarifying_questions": ["Could you please try again?"],
#     "confidence": 0.0
# }

# 3. If agent is offline:
# main.py endpoint checks: if agent.status != "healthy"
# Returns CLARIFICATION_NEEDED instead of error
return {
    "status": "CLARIFICATION_NEEDED",
    "reasoning": "The required specialist is currently offline"
}

# 4. If agent endpoint throws error:
try:
    agent_response = await forward_to_agent(agent_id, payload)
except Exception as e:
    _logger.error(f"Agent error: {e}")
    return {
        "status": "ERROR",
        "error": str(e)
    }
'''
    print(code)


# =============================================================================
# Example 7: Customization & Configuration
# =============================================================================

def example_7_customization():
    """Example: Customizing the orchestrator."""
    print("\n" + "="*60)
    print("EXAMPLE 7: Customization & Configuration")
    print("="*60)
    
    code = '''
# Create orchestrator with custom agent definitions
custom_agents = {
    "custom_agent": {
        "id": "custom_agent",
        "name": "My Custom Agent",
        "description": "Does something special",
        "capabilities": ["custom-capability"],
        "keywords": ["custom"],
        "required_params": ["param1"]
    }
}

orchestrator = create_orchestrator(agent_definitions=custom_agents)

# Adjust confidence thresholds
orchestrator.confidence_threshold = 0.80  # Higher threshold = more clarification
orchestrator.min_acceptable_confidence = 0.40

# Add custom formatter for new agent
def _format_for_custom_agent(self, payload, params):
    payload["custom_field"] = params.get("custom_param", "default")
    return payload

# Bind it to orchestrator
from types import MethodType
orchestrator._format_for_custom_agent = MethodType(_format_for_custom_agent, orchestrator)

# Override system prompt
def custom_build_system_prompt(self):
    # Your custom system prompt logic
    return "Custom system prompt..."

orchestrator._build_system_prompt = MethodType(custom_build_system_prompt, orchestrator)
'''
    print(code)


# =============================================================================
# Example 8: Integration with Memory Management
# =============================================================================

def example_8_memory_integration():
    """Example: How orchestrator integrates with conversation memory."""
    print("\n" + "="*60)
    print("EXAMPLE 8: Memory Management Integration")
    print("="*60)
    
    code = '''
# In main.py endpoint
from supervisor import memory_manager

user_id = user.id

# 1. Store user message
memory_manager.store_conversation_message(
    user_id=user_id,
    role="user",
    content=user_message
)

# 2. Process through orchestrator
orchestrator = get_orchestrator()
response = await orchestrator.process_message(user_message)

# 3. Store assistant response
if response.status == "READY_TO_ROUTE":
    # Forward to agent
    agent_response = await forward_to_agent(...)
    
    memory_manager.store_conversation_message(
        user_id=user_id,
        role="assistant",
        content=agent_response.response,
        agent_id=response.agent_id
    )
else:
    # Store clarification
    memory_manager.store_conversation_message(
        user_id=user_id,
        role="assistant",
        content=f"Clarification: {response.reasoning}"
    )

# 4. Retrieve history for next message
history = memory_manager.get_conversation_history(user_id, limit=10)
# Can pass to orchestrator if needed for multi-message context
'''
    print(code)


# =============================================================================
# Example 9: Testing & Debugging
# =============================================================================

def example_9_testing():
    """Example: Testing and debugging the orchestrator."""
    print("\n" + "="*60)
    print("EXAMPLE 9: Testing & Debugging")
    print("="*60)
    
    code = '''
# Run the test suite
# pytest supervisor/tests/test_gemini_chat_orchestrator.py -v

# Example test
import pytest
from supervisor.gemini_chat_orchestrator import create_orchestrator

def test_quiz_master_formatting():
    """Test that quiz master payload is correctly formatted."""
    orchestrator = create_orchestrator()
    
    payload = {"request": "Create quiz"}
    params = {"topic": "Python", "num_questions": 10}
    
    result = orchestrator._format_for_quiz_master(payload, params)
    
    assert result["topic"] == "Python"
    assert result["num_questions"] == 10

# Enable debug logging
import logging
logging.getLogger('supervisor.gemini_chat_orchestrator').setLevel(logging.DEBUG)

# Get state for debugging
orchestrator = get_orchestrator()
state = orchestrator.get_state()
print(f"Orchestrator state: {state}")

# Check conversation history
history = orchestrator.get_conversation_history()
for msg in history:
    print(f"{msg['role']}: {msg['content'][:50]}...")
'''
    print(code)


# =============================================================================
# Example 10: Production Deployment
# =============================================================================

def example_10_production():
    """Example: Production deployment considerations."""
    print("\n" + "="*60)
    print("EXAMPLE 10: Production Deployment")
    print("="*60)
    
    checklist = '''
Pre-Deployment Checklist:

[ ] GEMINI_API_KEY is set in environment variables
[ ] Agent registry is loaded correctly
    - Check: orchestrator.agents contains 5 agents
    - Check: Required parameters are identified for each agent

[ ] Test with staging data
    - Test clear requests (expected: READY_TO_ROUTE)
    - Test ambiguous requests (expected: CLARIFICATION_NEEDED)
    - Test all 5 agent types

[ ] Monitor metrics
    - Request latency (target: <1.5s)
    - Clarification rate (target: <20% of requests need clarification)
    - Agent routing accuracy (target: >95%)
    - API costs (target: <$0.1 per request)

[ ] Set up error logging
    - Log all Gemini API failures
    - Log JSON parsing errors
    - Log agent forwarding failures

[ ] Plan gradual rollout
    - Phase 1: 10% of users
    - Phase 2: 50% of users
    - Phase 3: 100% of users

[ ] Have rollback plan
    - Keep old endpoint available for 30 days
    - Monitor error rates
    - Be ready to revert to old system if needed

Deployment Command:
$ docker-compose up -d supervisor

Check Endpoint:
$ curl http://localhost:8000/api/supervisor/registry

Test Endpoint:
$ curl -X POST http://localhost:8000/api/supervisor/request-unified \\
  -H "Authorization: Bearer TEST_TOKEN" \\
  -d '{"request":"Create a quiz"}'
'''
    print(checklist)


# =============================================================================
# Main - Run All Examples
# =============================================================================

async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("UNIFIED GEMINI CHAT ORCHESTRATOR - USAGE EXAMPLES")
    print("="*70)
    
    # Example 1
    await example_1_direct_usage()
    
    # Example 2
    example_2_fastapi_integration()
    
    # Example 3
    example_3_http_api()
    
    # Example 4
    await example_4_all_agent_types()
    
    # Example 5
    await example_5_conversation_state()
    
    # Example 6
    example_6_error_handling()
    
    # Example 7
    example_7_customization()
    
    # Example 8
    example_8_memory_integration()
    
    # Example 9
    example_9_testing()
    
    # Example 10
    example_10_production()
    
    print("\n" + "="*70)
    print("END OF EXAMPLES")
    print("="*70)
    print("\nFor more information, see: GEMINI_ORCHESTRATOR_MIGRATION_GUIDE.md")


if __name__ == "__main__":
    asyncio.run(main())
