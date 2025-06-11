def generate_response(intent: str, entities: dict = None) -> str:
    entities = entities or {}
    if intent == "greeting":
        return "Hello! I'm your app building agent. How can I help you today?"
    elif intent == "clarification":
        return "Could you please provide more details?"
    elif intent == "confirmation":
        return "Okay, I will proceed with that."
    elif intent == "unknown_intent":
        return "I'm sorry, I didn't quite understand that. Could you try rephrasing?"
    elif intent == "create_script":
        script_name = entities.get("script_name", "your_script.py")
        return f"Alright, I'll start creating the script named '{script_name}'."
    elif intent == "add_function":
        func_name = entities.get("function_name", "your_function")
        target_script = entities.get("target_script") 
        
        if target_script:
            return f"Okay, I'll add the function '{func_name}' to '{target_script}'."
        else:
            return f"Okay, I'll define a function named '{func_name}'. Which script should it go into?"
    elif intent == "specify_language":
        language = entities.get("language", "the specified language")
        return f"Got it! I'll use {language} for future code generation tasks."
    elif intent == "add_print_statement":
        func_name = entities.get("function_name", "target_function")
        expr = entities.get("expression", "something")
        target_script = entities.get("target_script", "the current script")
        return f"Okay, I'll try to add a statement to print '{expr}' in function '{func_name}' within '{target_script}'."
    elif intent == "add_return_statement":
        func_name = entities.get("function_name", "target_function")
        expr = entities.get("expression", "something")
        target_script = entities.get("target_script", "the current script")
        return f"Okay, I'll try to add a statement to return '{expr}' from function '{func_name}' within '{target_script}'."
    else:
        return "I'm processing your request."

def ask_clarification(question: str) -> str:
    return f"To help me understand better: {question}"

def confirm_action(action_description: str) -> str:
    return f"Just to confirm, you want me to: {action_description} Is that correct?"
