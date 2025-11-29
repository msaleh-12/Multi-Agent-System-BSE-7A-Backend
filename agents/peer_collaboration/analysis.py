# agents/peer_collaboration/analysis.py

from textblob import TextBlob
from collections import Counter

def analyze_discussion(request: dict):
    content = request.get("content", {})
    logs = content.get("discussion_logs", [])
    members = request.get("team_members", [])

    # Count messages per user
    participation = {}
    for log in logs:
        uid = log["user_id"]
        participation[uid] = participation.get(uid, 0) + 1

    active_participants = [u for u, c in participation.items() if c > 2]
    inactive_participants = [u for u in members if u not in active_participants]

    # Analyze tone
    full_text = " ".join([msg["message"] for msg in logs])
    sentiment = TextBlob(full_text).sentiment.polarity
    tone = "positive" if sentiment > 0.1 else "negative" if sentiment < -0.1 else "neutral"

    # Extract dominant topics (simple keyword frequency)
    words = [w.lower() for w in full_text.split() if len(w) > 4]
    common = [w for w, _ in Counter(words).most_common(5)]

    # Compute simple score
    engagement_score = min(100, len(active_participants) * 15 + max(0, sentiment * 20))

    from .suggestions import generate_suggestions
    suggestions = generate_suggestions(active_participants, inactive_participants, tone)

    return {
        "status": "success",
        "collaboration_summary": {
            "active_participants": active_participants,
            "inactive_participants": inactive_participants,
            "discussion_sentiment": tone,
            "dominant_topics": common
        },
        "improvement_suggestions": suggestions,
        "collaboration_score": round(engagement_score, 2)
    }
