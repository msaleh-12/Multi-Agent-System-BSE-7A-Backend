# agents/peer_collaboration/tests/test_peer_collaboration.py

from agents.peer_collaboration.analysis import analyze_discussion

def test_basic_analysis():
    sample_request = {
        "project_id": "proj1",
        "team_members": ["u1", "u2", "u3"],
        "action": "analyze_discussion",
        "content": {
            "discussion_logs": [
                {"user_id": "u1", "timestamp": "2025-11-12T10:00:00Z", "message": "Let's finalize our tasks"},
                {"user_id": "u2", "timestamp": "2025-11-12T10:01:00Z", "message": "I can handle documentation"},
            ]
        }
    }

    result = analyze_discussion(sample_request)
    assert result["status"] == "success"
    assert "collaboration_summary" in result
