import re

def parse_intent(user_text: str) -> dict:
    user_text_lower = user_text.lower()
    entities = {}

    # create_script
    match_create_script = re.search(r"(?:create|make|new) (?:a|new)?\s*script (?:named|called)?\s*([a-zA-Z0-9_.-]+?)(?:\.py)?", user_text_lower)
    if match_create_script:
        script_name = match_create_script.group(1)
        if not script_name.endswith(".py"): script_name += ".py"
        entities["script_name"] = script_name
        return {"intent": "create_script", "entities": entities}

    # add_function
    match_add_function = re.search(r"(?:add|define) (?:a )?function (?:named|called)?\s*([a-zA-Z0-9_]+)\s*(?:\((.*?)\))?", user_text_lower)
    if match_add_function:
        entities["function_name"] = match_add_function.group(1)
        parameters_str = match_add_function.group(2)
        if parameters_str: entities["parameters"] = [p.strip() for p in parameters_str.split(',') if p.strip()]
        else: entities["parameters"] = []
        # Target script for add_function is usually specified with "to script" or "in script"
        match_target_script = re.search(r"(?:to|in) (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?", user_text_lower)
        if match_target_script:
            script_name = match_target_script.group(1)
            if not script_name.endswith(".py"): script_name += ".py"
            entities["target_script"] = script_name
        return {"intent": "add_function", "entities": entities}

    # add_print_statement
    # Example: "in function my_func print 'hello'" or "in function my_func in script x.py print 'hello'"
    match_print = re.search(
        r"in (?:function\s*)?([a-zA-Z0-9_]+)\s*" # Function name: group(1)
        r"(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?" # Optional target script for the function: group(2)
        r"print\s+(.+)", # Value to print: group(3)
        user_text_lower)
    if match_print:
        entities["function_name"] = match_print.group(1)
        if match_print.group(2): # target_script for the function's location
            script_name = match_print.group(2).strip()
            if not script_name.endswith(".py"): script_name += ".py"
            entities["target_script"] = script_name
        entities["expression"] = match_print.group(3).strip()
        if (entities["expression"].startswith("'") and entities["expression"].endswith("'")) or \
           (entities["expression"].startswith('"') and entities["expression"].endswith('"')):
            entities["expression_type"] = "literal_string"; entities["value"] = entities["expression"][1:-1]
        else:
            entities["expression_type"] = "variable_or_expr"; entities["value"] = entities["expression"]
        return {"intent": "add_print_statement", "entities": entities}

    # add_return_statement
    match_return = re.search(
        r"in (?:function\s*)?([a-zA-Z0-9_]+)\s*" # Function name: group(1)
        r"(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?" # Optional target script for the function: group(2)
        r"return\s+(.+)", # Value to return: group(3)
        user_text_lower)
    if match_return:
        entities["function_name"] = match_return.group(1)
        if match_return.group(2): # target_script for the function's location
            script_name = match_return.group(2).strip()
            if not script_name.endswith(".py"): script_name += ".py"
            entities["target_script"] = script_name
        entities["expression"] = match_return.group(3).strip()
        return {"intent": "add_return_statement", "entities": entities}

    # add_import_statement
    match_from_import = re.search(r"from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_,\s]+)(?:\s+into\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?", user_text_lower)
    if match_from_import:
        entities["import_type"] = "from_import"; entities["module"] = match_from_import.group(1).strip()
        entities["names"] = [name.strip() for name in match_from_import.group(2).split(',') if name.strip()]
        if match_from_import.group(3):
            script_name = match_from_import.group(3).strip()
            if not script_name.endswith(".py"): script_name += ".py"
            entities["target_script"] = script_name
        return {"intent": "add_import_statement", "entities": entities}

    match_direct_import = re.search(r"import\s+([a-zA-Z0-9_,\s]+)(?:\s+into\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?", user_text_lower)
    if match_direct_import:
        # Check if "from " precedes "import" to avoid misinterpreting "from ... import"
        # This is a basic check; more robust parsing might be needed for complex cases.
        from_keyword_present_before = False
        if "from " in user_text_lower:
            try:
                from_idx = user_text_lower.index("from ")
                import_idx = user_text_lower.index("import ") # Ensure this refers to the main "import" keyword
                # Check if "from" is before "import" and not part of a module name like "import fromsomething"
                if from_idx < import_idx and user_text_lower[from_idx:import_idx].count("import") == 0:
                    # Check if the text between "from" and "import" is just whitespace or module names,
                    # not another "import" keyword, which would imply separate statements.
                    from_keyword_present_before = True
            except ValueError: # "import " not found, should not happen if match_direct_import succeeded.
                pass

        if not from_keyword_present_before:
            entities["import_type"] = "direct_import"; entities["modules"] = [mod.strip() for mod in match_direct_import.group(1).split(',') if mod.strip()]
            if match_direct_import.group(2):
                script_name = match_direct_import.group(2).strip()
                if not script_name.endswith(".py"): script_name += ".py"
                entities["target_script"] = script_name
            return {"intent": "add_import_statement", "entities": entities}

    # create_class_statement
    match_create_class = re.search(r"(?:create|make|new) class\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+in\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?", user_text_lower)
    if match_create_class:
        entities["class_name"] = match_create_class.group(1).strip()
        if match_create_class.group(2):
            script_name = match_create_class.group(2).strip()
            if not script_name.endswith(".py"): script_name += ".py"
            entities["target_script"] = script_name
        return {"intent": "create_class_statement", "entities": entities}

    # specify_language
    match_language = re.search(r"(?:use|with|in)\s+(python|javascript|java|c\+\+)", user_text_lower)
    if match_language:
        entities["language"] = match_language.group(1)
        return {"intent": "specify_language", "entities": entities}

    return {"intent": "unknown", "entities": {}}
