import re

def parse_intent(user_text: str) -> dict:
    user_text_lower = user_text.lower()
    entities = {}

    # Intent: create_script (remains the same)
    match_create_script = re.search(r"create (?:a|new) script (?:named|called)?\s*([a-zA-Z0-9_.-]+?)(?:\.py)?", user_text_lower)
    if match_create_script:
        script_name = match_create_script.group(1)
        if not script_name.endswith(".py"):
            script_name += ".py"
        entities["script_name"] = script_name
        return {"intent": "create_script", "entities": entities}

    # Intent: add_function (remains the same)
    match_add_function = re.search(
        r"add (?:a )?function (?:named|called)?\s*([a-zA-Z0-9_]+)\s*(?:\((.*?)\))?", 
        user_text_lower
    )
    if match_add_function:
        entities["function_name"] = match_add_function.group(1)
        parameters_str = match_add_function.group(2)
        if parameters_str:
            entities["parameters"] = [p.strip() for p in parameters_str.split(',') if p.strip()]
        else:
            entities["parameters"] = [] 
        match_target_script = re.search(r"to (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?", user_text_lower)
        if match_target_script:
            script_name = match_target_script.group(1)
            if not script_name.endswith(".py"):
                script_name += ".py"
            entities["target_script"] = script_name
        return {"intent": "add_function", "entities": entities}

    # Intent: add_print_statement
    # Example: "in function my_func print 'hello'" or "in my_func print variable_name"
    # Regex: 1=function_name, 2=value_to_print (string or variable)
    # Adjusted to better capture target script if specified with "in script"
    match_print = re.search(
        r"in (?:function\s*)?([a-zA-Z0-9_]+)\s+print\s+(.+?)(?:\s+in script\s*([a-zA-Z0-9_.-]+?)(?:\.py)?)?$", 
        user_text_lower
    )
    if match_print:
        entities["function_name"] = match_print.group(1)
        entities["expression"] = match_print.group(2).strip()
        
        if (entities["expression"].startswith("'") and entities["expression"].endswith("'")) or \
           (entities["expression"].startswith('"') and entities["expression"].endswith('"')):
            entities["expression_type"] = "literal_string"
            entities["value"] = entities["expression"][1:-1] # Store raw string for ast.Constant
        else:
            entities["expression_type"] = "variable_or_expr"
            entities["value"] = entities["expression"] # Pass the raw expression string

        if match_print.group(3): # Optional target script was captured
            script_name = match_print.group(3)
            if not script_name.endswith(".py"):
                script_name += ".py"
            entities["target_script"] = script_name
        return {"intent": "add_print_statement", "entities": entities}

    # Intent: add_return_statement
    # Example: "in function my_func return result" or "in my_func return a + b"
    # Adjusted to better capture target script if specified with "in script"
    match_return = re.search(
        r"in (?:function\s*)?([a-zA-Z0-9_]+)\s+return\s+(.+?)(?:\s+in script\s*([a-zA-Z0-9_.-]+?)(?:\.py)?)?$", 
        user_text_lower
    )
    if match_return:
        entities["function_name"] = match_return.group(1)
        entities["expression"] = match_return.group(2).strip() # Pass raw expression string
        # No specific expression_type needed for return for now, generator will parse
        
        if match_return.group(3): # Optional target script
            script_name = match_return.group(3)
            if not script_name.endswith(".py"):
                script_name += ".py"
            entities["target_script"] = script_name
        return {"intent": "add_return_statement", "entities": entities}

    # Intent: specify_language (remains the same)
    match_language = re.search(r"(?:use|with|in)\s+(python|javascript|java|c\+\+)", user_text_lower)
    if match_language:
        entities["language"] = match_language.group(1)
        return {"intent": "specify_language", "entities": entities}
        
    return {"intent": "unknown", "entities": {}}
