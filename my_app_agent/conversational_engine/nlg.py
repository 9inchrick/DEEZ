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
    elif intent == "specify_language":
        language = entities.get("language", "the specified language")
        if language.lower() == "javascript":
            return f"Okay! Switched to JavaScript mode. Capabilities are currently limited to creating basic script files."
        elif language.lower() == "python":
            return f"Got it! Switched back to Python mode."
        else:
            return f"Got it! I'll use {language} for future tasks, though support might be limited." # Generic
    elif intent == "create_script": # Modify this to be language aware for NLG
        script_name = entities.get("script_name", "your_script")
        language = entities.get("current_language", "the current language") # Agent should pass this
        if language.lower() == "javascript":
            if not script_name.endswith(".js"): script_name += ".js"
            return f"Alright, I'll start creating the JavaScript script named '{script_name}'."
        else: # Default to Python or other languages
            if not script_name.endswith(".py") and language.lower() == "python": script_name += ".py"
            return f"Alright, I'll start creating the script named '{script_name}'."
    elif intent == "add_function":
        func_name = entities.get("function_name", "your_function")
        target_script = entities.get("target_script")
        if target_script:
            return f"Okay, I'll add the function '{func_name}' to '{target_script}'."
        else:
            return f"Okay, I'll define a function named '{func_name}'. Which script should it go into?"
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
    elif intent == "add_import_statement":
        import_type = entities.get("import_type", "import")
        target_script = entities.get("target_script", "the current script")
        import_desc = ""
        if import_type == "direct_import":
            modules = ", ".join(entities.get("modules", ["something"]))
            import_desc = f"`import {modules}`"
        elif import_type == "from_import":
            module_name = entities.get("module", "somemodule")
            names = ", ".join(entities.get("names", ["something"]))
            import_desc = f"`from {module_name} import {names}`"
        else:
            import_desc = "the specified import"
        return f"Okay, I'll try to add {import_desc} to '{target_script}'."
    elif intent == "create_class_statement":
        class_name = entities.get("class_name", "SomeClass")
        target_script = entities.get("target_script", "the current script")
        return f"Okay, I'll try to create an empty class named '{class_name}' in '{target_script}'."
    else:
        return "I'm processing your request."

def ask_clarification(question: str) -> str:
    return f"To help me understand better: {question}"

def confirm_action(action_description: str) -> str:
    return f"Just to confirm, you want me to: {action_description} Is that correct?"
