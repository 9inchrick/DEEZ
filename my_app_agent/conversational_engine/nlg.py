def generate_response(intent: str, data: dict = None) -> str:
    if intent == "greeting":
        return "Hello! How can I help you build an app today?"
    elif intent == "clarification":
        return "Could you please provide more details?"
    elif intent == "confirmation":
        return f"Okay, I will proceed with that."
    elif intent == "unknown_intent":
        return "I'm sorry, I didn't understand that. Could you rephrase?"
    else:
        return "I'm processing your request."

def ask_clarification(question: str) -> str:
    return f"To help me understand better: {question}"
