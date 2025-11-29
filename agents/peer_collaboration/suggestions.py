# agents/peer_collaboration/suggestions.py

def generate_suggestions(active, inactive, tone):
    suggestions = []

    if inactive:
        suggestions.append("Encourage quieter members to share updates.")

    if tone == "negative":
        suggestions.append("Address team tensions through an open discussion.")
    elif tone == "neutral":
        suggestions.append("Add positive feedback to boost motivation.")

    if len(active) > 0 and len(inactive) > len(active):
        suggestions.append("Clarify task ownership to reduce confusion.")

    suggestions.append("Schedule short weekly syncs to maintain progress.")

    return suggestions
