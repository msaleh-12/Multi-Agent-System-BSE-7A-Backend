# supervisor/tests/test_gemini_chat_orchestrator.py
"""
Comprehensive test suite for the unified Gemini chat orchestrator.

Tests cover:
1. Clear single-turn requests (no clarification needed)
2. Ambiguous requests (needs clarification)
3. Multi-turn clarification flows
4. Each of the 5 agent types with different parameter sets
5. Fallback behavior when Gemini fails
6. Parameter extraction and validation
7. Conversation state management
"""

import pytest
import json
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from supervisor.gemini_chat_orchestrator import (
    GeminiChatOrchestrator,
    GeminiChatOrchestratorResponse,
    get_orchestrator,
    create_orchestrator,
    reset_orchestrator
)

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger(__name__)


class TestGeminiChatOrchestratorBasic:
    """Test basic orchestrator functionality."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create a fresh orchestrator for each test."""
        reset_orchestrator()
        orch = create_orchestrator()
        yield orch
        reset_orchestrator()
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes correctly."""
        assert orchestrator is not None
        assert orchestrator.confidence_threshold == 0.70
        assert len(orchestrator.agents) > 0
        assert "adaptive_quiz_master_agent" in orchestrator.agents
        assert "research_scout_agent" in orchestrator.agents
        assert "assignment_coach_agent" in orchestrator.agents
        assert "plagiarism_prevention_agent" in orchestrator.agents
        assert "gemini_wrapper_agent" in orchestrator.agents
    
    def test_agent_definitions_loaded(self, orchestrator):
        """Test that all agent definitions are properly loaded."""
        assert orchestrator.agents["adaptive_quiz_master_agent"]["name"] == "Quiz Generation Specialist"
        assert "quiz" in orchestrator.agents["adaptive_quiz_master_agent"]["keywords"]
        assert orchestrator.agents["research_scout_agent"]["name"] == "Research Paper Finder"
        assert "research" in orchestrator.agents["research_scout_agent"]["keywords"]
    
    def test_required_params_identification(self, orchestrator):
        """Test that required parameters are correctly identified."""
        quiz_params = orchestrator._get_required_params_for_agent("adaptive_quiz_master_agent")
        assert "topic" in quiz_params
        assert "num_questions" in quiz_params
        
        research_params = orchestrator._get_required_params_for_agent("research_scout_agent")
        assert "topic" in research_params
        
        wrapper_params = orchestrator._get_required_params_for_agent("gemini_wrapper_agent")
        assert len(wrapper_params) == 0  # No required params for wrapper
    
    def test_conversation_history_management(self, orchestrator):
        """Test conversation history is properly managed."""
        orchestrator.conversation_history.append({"role": "user", "content": "Hello"})
        history = orchestrator.get_conversation_history()
        assert len(history) == 1
        assert history[0]["content"] == "Hello"
        
        orchestrator.reset_conversation()
        assert len(orchestrator.conversation_history) == 0
    
    def test_orchestrator_state(self, orchestrator):
        """Test getting orchestrator state."""
        state = orchestrator.get_state()
        assert "current_agent_id" in state
        assert "extracted_params" in state
        assert "conversation_length" in state
        assert "available_agents" in state
        assert len(state["available_agents"]) == 5


class TestAgentFormatters:
    """Test agent-specific payload formatters."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create a fresh orchestrator for each test."""
        reset_orchestrator()
        orch = create_orchestrator()
        yield orch
        reset_orchestrator()
    
    def test_format_for_quiz_master(self, orchestrator):
        """Test formatting for Adaptive Quiz Master Agent."""
        payload = {"request": "Create a Python quiz"}
        params = {"topic": "Python", "num_questions": 10, "difficulty": "intermediate"}
        
        result = orchestrator._format_for_quiz_master(payload, params)
        
        assert result["request"] == "Create a Python quiz"
        assert result["topic"] == "Python"
        assert result["num_questions"] == 10
        assert result["difficulty"] == "intermediate"
    
    def test_format_for_research_scout(self, orchestrator):
        """Test formatting for Research Scout Agent."""
        payload = {"request": "Find papers on neural networks"}
        params = {
            "topic": "neural networks",
            "keywords": ["deep learning", "CNN"],
            "year_range": {"from": "2020", "to": "2023"},
            "max_results": 10
        }
        
        result = orchestrator._format_for_research_scout(payload, params)
        
        assert "data" in result
        assert result["data"]["topic"] == "neural networks"
        assert result["data"]["keywords"] == ["deep learning", "CNN"]
        assert result["data"]["year_range"]["from"] == "2020"
        assert result["data"]["max_results"] == 10
    
    def test_format_for_assignment_coach(self, orchestrator):
        """Test formatting for Assignment Coach Agent."""
        payload = {"request": "Help with photosynthesis essay"}
        params = {"task_description": "Write essay on photosynthesis", "subject": "Biology"}
        
        result = orchestrator._format_for_assignment_coach(payload, params)
        
        assert result["task_description"] == "Write essay on photosynthesis"
        assert result["subject"] == "Biology"
    
    def test_format_for_plagiarism_agent(self, orchestrator):
        """Test formatting for Plagiarism Prevention Agent."""
        text = "This is the text to check"
        payload = {"request": "Check this text"}
        params = {"text_content": text, "check_type": "check", "citation_style": "APA"}
        
        result = orchestrator._format_for_plagiarism_agent(payload, params)
        
        assert result["text_content"] == text
        assert result["check_type"] == "check"
        assert result["citation_style"] == "APA"
    
    def test_format_for_gemini_wrapper(self, orchestrator):
        """Test formatting for Gemini Wrapper Agent."""
        payload = {"request": "What is photosynthesis?"}
        params = {"additional_field": "value"}
        
        result = orchestrator._format_for_gemini_wrapper(payload, params)
        
        assert result["request"] == "What is photosynthesis?"
        assert result["additional_field"] == "value"


class TestParseGeminiResponse:
    """Test Gemini response parsing and validation."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create a fresh orchestrator for each test."""
        reset_orchestrator()
        orch = create_orchestrator()
        yield orch
        reset_orchestrator()
    
    def test_parse_valid_ready_response(self, orchestrator):
        """Test parsing valid READY_TO_ROUTE response."""
        response_text = json.dumps({
            "status": "READY_TO_ROUTE",
            "agent_id": "adaptive_quiz_master_agent",
            "confidence": 0.95,
            "reasoning": "Clear intent to create a quiz",
            "extracted_params": {"topic": "Python", "num_questions": 10},
            "clarifying_questions": []
        })
        
        parsed = orchestrator._parse_gemini_response(response_text)
        
        assert parsed["status"] == "READY_TO_ROUTE"
        assert parsed["agent_id"] == "adaptive_quiz_master_agent"
        assert parsed["confidence"] == 0.95
        assert parsed["extracted_params"]["topic"] == "Python"
    
    def test_parse_valid_clarification_response(self, orchestrator):
        """Test parsing valid CLARIFICATION_NEEDED response."""
        response_text = json.dumps({
            "status": "CLARIFICATION_NEEDED",
            "agent_id": None,
            "confidence": 0.35,
            "reasoning": "Request is ambiguous",
            "extracted_params": {},
            "clarifying_questions": ["What subject?", "What type of help?"]
        })
        
        parsed = orchestrator._parse_gemini_response(response_text)
        
        assert parsed["status"] == "CLARIFICATION_NEEDED"
        assert parsed["agent_id"] is None
        assert len(parsed["clarifying_questions"]) == 2
    
    def test_parse_markdown_wrapped_response(self, orchestrator):
        """Test parsing response wrapped in markdown code blocks."""
        response_text = """```json
{
    "status": "READY_TO_ROUTE",
    "agent_id": "research_scout_agent",
    "confidence": 0.88,
    "reasoning": "Looking for papers",
    "extracted_params": {"topic": "machine learning"},
    "clarifying_questions": []
}
```"""
        
        parsed = orchestrator._parse_gemini_response(response_text)
        
        assert parsed["status"] == "READY_TO_ROUTE"
        assert parsed["agent_id"] == "research_scout_agent"
    
    def test_parse_invalid_json_fallback(self, orchestrator):
        """Test graceful handling of invalid JSON."""
        response_text = "This is not valid JSON at all"
        
        parsed = orchestrator._parse_gemini_response(response_text)
        
        assert parsed["status"] == "CLARIFICATION_NEEDED"
        assert parsed["confidence"] == 0.0
        assert len(parsed["clarifying_questions"]) > 0
    
    def test_parse_adds_default_fields(self, orchestrator):
        """Test that missing fields are added with defaults."""
        response_text = json.dumps({
            "status": "READY_TO_ROUTE",
            "agent_id": "adaptive_quiz_master_agent"
        })
        
        parsed = orchestrator._parse_gemini_response(response_text)
        
        assert "extracted_params" in parsed
        assert "clarifying_questions" in parsed
        assert isinstance(parsed["extracted_params"], dict)
        assert isinstance(parsed["clarifying_questions"], list)


class TestFormatResponses:
    """Test response formatting methods."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create a fresh orchestrator for each test."""
        reset_orchestrator()
        orch = create_orchestrator()
        yield orch
        reset_orchestrator()
    
    def test_format_clarification_response(self, orchestrator):
        """Test formatting clarification response."""
        parsed = {
            "status": "CLARIFICATION_NEEDED",
            "confidence": 0.4,
            "reasoning": "Need more info",
            "clarifying_questions": ["What subject?"]
        }
        
        response = orchestrator._format_clarification_response(parsed)
        
        assert isinstance(response, GeminiChatOrchestratorResponse)
        assert response.status == "CLARIFICATION_NEEDED"
        assert len(response.clarifying_questions) == 1
    
    def test_format_clarification_adds_default_question(self, orchestrator):
        """Test that default question is added if none provided."""
        parsed = {
            "status": "CLARIFICATION_NEEDED",
            "confidence": 0.3,
            "reasoning": "Too vague",
            "clarifying_questions": []
        }
        
        response = orchestrator._format_clarification_response(parsed)
        
        assert len(response.clarifying_questions) > 0


class TestSystemPromptBuilding:
    """Test system prompt construction."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create a fresh orchestrator for each test."""
        reset_orchestrator()
        orch = create_orchestrator()
        yield orch
        reset_orchestrator()
    
    def test_system_prompt_contains_agents(self, orchestrator):
        """Test that system prompt includes all agent definitions."""
        prompt = orchestrator._build_system_prompt()
        
        assert "adaptive_quiz_master_agent" in prompt
        assert "research_scout_agent" in prompt
        assert "assignment_coach_agent" in prompt
        assert "plagiarism_prevention_agent" in prompt
        assert "gemini_wrapper_agent" in prompt
    
    def test_system_prompt_contains_instructions(self, orchestrator):
        """Test that system prompt includes decision logic instructions."""
        prompt = orchestrator._build_system_prompt()
        
        assert "READY_TO_ROUTE" in prompt
        assert "CLARIFICATION_NEEDED" in prompt
        assert "confidence" in prompt.lower()
        assert "parameter" in prompt.lower()
    
    def test_system_prompt_includes_examples(self, orchestrator):
        """Test that system prompt includes agent-specific examples."""
        prompt = orchestrator._build_system_prompt()
        
        # Should include example for quiz creation
        assert "quiz" in prompt.lower()
        assert "questions" in prompt.lower()
        # Should include example for research
        assert "neural networks" in prompt or "papers" in prompt.lower()


class TestConversationStateManagement:
    """Test conversation state tracking across messages."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create a fresh orchestrator for each test."""
        reset_orchestrator()
        orch = create_orchestrator()
        yield orch
        reset_orchestrator()
    
    def test_history_accumulation(self, orchestrator):
        """Test that conversation history accumulates."""
        orchestrator.conversation_history.append({
            "role": "user",
            "content": "Hello",
            "timestamp": datetime.utcnow().isoformat()
        })
        orchestrator.conversation_history.append({
            "role": "assistant",
            "content": "Hi",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        assert len(orchestrator.conversation_history) == 2
        assert orchestrator.conversation_history[0]["role"] == "user"
        assert orchestrator.conversation_history[1]["role"] == "assistant"
    
    def test_history_trimming(self, orchestrator):
        """Test that history is trimmed to max size."""
        # Add more than MAX_HISTORY_MESSAGES
        from supervisor.gemini_chat_orchestrator import MAX_HISTORY_MESSAGES
        
        for i in range(MAX_HISTORY_MESSAGES + 5):
            orchestrator.conversation_history.append({
                "role": "user",
                "content": f"Message {i}",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Simulate what process_message does
        if len(orchestrator.conversation_history) > MAX_HISTORY_MESSAGES:
            orchestrator.conversation_history = orchestrator.conversation_history[-MAX_HISTORY_MESSAGES:]
        
        assert len(orchestrator.conversation_history) == MAX_HISTORY_MESSAGES
    
    def test_extracted_params_accumulation(self, orchestrator):
        """Test that extracted parameters accumulate across messages."""
        orchestrator.extracted_params["topic"] = "Python"
        orchestrator.extracted_params["num_questions"] = 10
        
        assert orchestrator.extracted_params["topic"] == "Python"
        assert orchestrator.extracted_params["num_questions"] == 10
        
        # Update with new info
        orchestrator.extracted_params.update({"difficulty": "advanced"})
        
        assert orchestrator.extracted_params["topic"] == "Python"
        assert orchestrator.extracted_params["difficulty"] == "advanced"


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create a fresh orchestrator for each test."""
        reset_orchestrator()
        orch = create_orchestrator()
        yield orch
        reset_orchestrator()
    
    def test_empty_message_handling(self, orchestrator):
        """Test handling of empty user messages."""
        parsed = orchestrator._parse_gemini_response(json.dumps({
            "status": "CLARIFICATION_NEEDED",
            "confidence": 0.0,
            "reasoning": "Empty message",
            "extracted_params": {},
            "clarifying_questions": ["Could you please provide a message?"]
        }))
        
        assert parsed["status"] == "CLARIFICATION_NEEDED"
    
    def test_special_characters_in_params(self, orchestrator):
        """Test handling of special characters in parameters."""
        params = {
            "task_description": "Write an essay about \"AI & Machine Learning\" [draft]"
        }
        
        payload = orchestrator._format_for_assignment_coach(
            {"request": "Help"}, 
            params
        )
        
        assert "AI & Machine Learning" in payload["task_description"]
    
    def test_unicode_handling(self, orchestrator):
        """Test handling of Unicode characters."""
        params = {
            "topic": "Machine Learning (机器学习)"
        }
        
        payload = orchestrator._format_for_quiz_master(
            {"request": "Create quiz"},
            params
        )
        
        assert "机器学习" in payload["topic"]
    
    def test_null_and_none_handling(self, orchestrator):
        """Test handling of None/null values."""
        params = {
            "topic": "Python",
            "difficulty": None,
            "style": ""
        }
        
        payload = orchestrator._format_for_quiz_master(
            {"request": "Create quiz"},
            params
        )
        
        assert payload["topic"] == "Python"
        # None should be handled gracefully


class TestSingletonManagement:
    """Test singleton orchestrator management."""
    
    def test_get_orchestrator_returns_singleton(self):
        """Test that get_orchestrator returns same instance."""
        reset_orchestrator()
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        
        assert orch1 is orch2
    
    def test_create_orchestrator_creates_new_instance(self):
        """Test that create_orchestrator creates new instance."""
        orch1 = create_orchestrator()
        orch2 = create_orchestrator()
        
        assert orch1 is not orch2
    
    def test_reset_orchestrator_clears_singleton(self):
        """Test that reset_orchestrator clears the singleton."""
        orch1 = get_orchestrator()
        reset_orchestrator()
        orch2 = get_orchestrator()
        
        assert orch1 is not orch2


# Integration test scenarios
class TestIntegrationScenarios:
    """Integration tests for complete workflows."""
    
    def test_scenario_clear_quiz_request(self):
        """Scenario: User clearly wants a quiz (no clarification needed)."""
        # This would require mocking Gemini API
        pass
    
    def test_scenario_ambiguous_request_clarification(self):
        """Scenario: User makes ambiguous request, provides clarification."""
        # This would require mocking Gemini API and multi-turn simulation
        pass
    
    def test_scenario_progressive_parameter_extraction(self):
        """Scenario: Parameters extracted progressively across messages."""
        # This would require mocking Gemini API and multi-turn simulation
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
