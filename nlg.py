def generate_response(intent: str, entities: dict = None) -> str:
    entities = entities or {}
    target_script = entities.get("target_script", "the current script") 

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
            return f"Got it! I'll use {language} for future tasks, though support might be limited." 
    elif intent == "create_script": 
        script_name = entities.get("script_name", "your_script")
        language = entities.get("current_language", "the current language") 
        if language.lower() == "javascript":
            if not script_name.endswith(".js"): script_name += ".js"
            return f"Alright, I'll start creating the JavaScript script named '{script_name}'."
        else: 
            if not script_name.endswith(".py") and language.lower() == "python": script_name += ".py"
            return f"Alright, I'll start creating the script named '{script_name}'."
    elif intent == "add_function": 
        func_name = entities.get("function_name", "your_function")
        return f"Okay, I'll add the function '{func_name}' to '{target_script}'."
    elif intent == "add_method_to_class":
        class_name = entities.get("class_name", "TargetClass")
        method_name = entities.get("method_name", "new_method") 
        return f"Okay, I'll try to add method '{method_name}' to class '{class_name}' in '{target_script}'."
    elif intent == "add_class_attribute": 
        class_name = entities.get("class_name", "TargetClass")
        attr_name = entities.get("attribute_name", "new_attribute")
        value_expr = entities.get("value_expression", "None")
        return f"Okay, I'll try to add attribute {attr_name} = {value_expr} to class '{class_name}' in '{target_script}'."
    elif intent == "add_instance_attribute": 
        class_name = entities.get("class_name", "TargetClass")
        attr_name = entities.get("attribute_name", "new_attr")
        value_expr = entities.get("value_expression", "None")
        return f"Okay, I'll try to add instance attribute self.{attr_name} = {value_expr} to __init__ of class '{class_name}' in '{target_script}'."
    elif intent == "add_decorator": 
        item_name = entities.get("item_name", "target_function_or_method")
        class_name = entities.get("class_name")
        decorator_expr = entities.get("decorator_expression", "unknown_decorator")
        target_desc = f"method '{item_name}' in class '{class_name}'" if class_name else f"function '{item_name}'"
        return f"Okay, I'll try to add decorator '@{decorator_expr}' to {target_desc} in '{target_script}'."
    
    elif intent in ["add_print_statement", "add_return_statement", "add_conditional_statement", "add_for_loop", "add_while_loop", "add_file_operation", "add_try_except"]:
        item_name = entities.get("item_name", entities.get("function_name", "the target function/method")) 
        class_name_context = entities.get("class_name")
        action_description = ""
        if intent == "add_print_statement": action_description = f"print '{entities.get('expression', 'something')}'"
        elif intent == "add_return_statement": action_description = f"return '{entities.get('expression', 'something')}'"
        elif intent == "add_conditional_statement": action_description = "a conditional (if/elif/else) statement"
        elif intent == "add_for_loop": action_description = "a for-loop"
        elif intent == "add_while_loop": action_description = "a while-loop"
        elif intent == "add_file_operation":
            file_name = entities.get("filename", "some_file"); mode = entities.get("file_mode", "r"); action_type = entities.get("file_action", {}).get("type", "do something")
            action_description = f"a file operation (open {file_name} mode '{mode}', then {action_type})"
        elif intent == "add_try_except":
            exception_type = entities.get("exception_type_str") or "any exception" # Handles None for bare except
            clauses = ["try", "except " + exception_type]
            if entities.get("else_body_command_descs"): clauses.append("else")
            if entities.get("finally_body_command_descs"): clauses.append("finally")
            action_description = f"a {', '.join(clauses)} block"

        target_location_desc = f"method '{item_name}' in class '{class_name_context}'" if class_name_context else f"function '{item_name}'"
        return f"Okay, I'll try to add {action_description} to {target_location_desc} within '{target_script}'."
            
    elif intent == "create_class_statement": 
        class_name = entities.get("class_name", "SomeClass")
        base_classes = entities.get("base_classes") 
        loc = f" in script '{target_script}'" if target_script and target_script != "the current script" else ""
        
        if base_classes: 
            bases_str = ", ".join(base_classes)
            return f"Okay, I'll try to create class '{class_name}' inheriting from '{bases_str}'{loc}."
        else:
            return f"Okay, I'll try to create an empty class named '{class_name}'{loc}."
    elif intent == "add_import_statement":
        import_type = entities.get("import_type", "import"); import_desc = ""
        if import_type == "direct_import": import_desc = f"`import {', '.join(entities.get('modules', ['something']))}`"
        elif import_type == "from_import": import_desc = f"`from {entities.get('module', 'somemodule')} import {', '.join(entities.get('names', ['something']))}`"
        else: import_desc = "the specified import"
        return f"Okay, I'll try to add {import_desc} to '{target_script}'."
    else: 
        return "I'm processing your request."

def ask_clarification(question: str) -> str:
    return f"To help me understand better: {question}"

def confirm_action(action_description: str) -> str:
    return f"Just to confirm, you want me to: {action_description} Is that correct?"
