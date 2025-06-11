import re
import ast # For literal_eval in add_instance_attribute heuristic

def parse_simple_body_command(command_str: str) -> dict:
    """Parses simple commands like 'print X', 'return Y', or 'var = Z' for loop/conditional/try-except bodies."""
    command_str = command_str.strip()

    match_assign = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)", command_str)
    if match_assign:
        target_var = match_assign.group(1).strip()
        value_expr = match_assign.group(2).strip()
        return {"type": "assign", "target": target_var, "expression": value_expr}

    match_return = re.match(r"return\s+(.+)", command_str)
    if match_return:
        expression = match_return.group(1).strip()
        return {"type": "return", "expression": expression}

    match_print = re.match(r"print\s+(.+)", command_str)
    if match_print:
        expression = match_print.group(1).strip()
        return {"type": "print", "expression": expression}

    if command_str == "pass": return {"type": "pass"}
    return {"type": "unknown_statement", "raw_command": command_str}

def parse_function_body_command_details(remaining_command: str, entities: dict, context_allows_file_op=True):
    """
    Helper to parse specific statement details (print, return, if, for, while, file_op, try_except)
    after function/method context is established.
    Modifies entities directly.
    Returns the intent string if a match is found, otherwise None.
    """
    # add_print_statement (within function/method body)
    match_print = re.match(r"print\s+(.+)", remaining_command)
    if match_print:
        entities["expression"] = match_print.group(1).strip()
        return "add_print_statement"

    match_return = re.match(r"return\s+(.+)", remaining_command)
    if match_return:
        entities["expression"] = match_return.group(1).strip()
        return "add_return_statement"

    match_if = re.match(r"if\s+(.+?)\s+(.+?)(?:\s+else\s+(.+))?", remaining_command)
    if match_if:
        entities["if_condition"] = match_if.group(1).strip()
        entities["if_body_command"] = parse_simple_body_command(match_if.group(2).strip())
        if match_if.group(3):
            entities["else_body_command"] = parse_simple_body_command(match_if.group(3).strip())
        else: entities["else_body_command"] = None
        return "add_conditional_statement"

    match_for = re.match(r"for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+(.+?)\s+(.+)", remaining_command)
    if match_for:
        entities["loop_variable"] = match_for.group(1).strip()
        entities["iterable_expression"] = match_for.group(2).strip()
        entities["body_command"] = parse_simple_body_command(match_for.group(3).strip())
        return "add_for_loop"

    match_while = re.match(r"while\s+(.+?)\s+(.+)", remaining_command)
    if match_while:
        entities["condition_expression"] = match_while.group(1).strip()
        entities["body_command"] = parse_simple_body_command(match_while.group(2).strip())
        return "add_while_loop"

    if context_allows_file_op: # File op is a bit more complex, might not be allowed in all body contexts by design
        match_file_op_body = re.match(r"open\s+(['\"].+?['\"])\s+for\s+(reading|writing|appending)\s+as\s+([a-zA-Z0-9_]+)\s+then\s+(.+)", remaining_command)
        if match_file_op_body:
            entities["filename"] = match_file_op_body.group(1).strip()
            mode_str = match_file_op_body.group(2).strip(); mode_map = {"reading": "r", "writing": "w", "appending": "a"}
            entities["file_mode"] = mode_map.get(mode_str, "r")
            entities["file_variable"] = match_file_op_body.group(3).strip()
            action_str = match_file_op_body.group(4).strip()
            action_assign_read_match = re.match(r"([a-zA-Z0-9_]+)\s*=\s*" + re.escape(entities["file_variable"]) + r"\.read\(\)", action_str)
            action_write_match = re.match(re.escape(entities["file_variable"]) + r"\.write\((.+)\)", action_str)
            action_read_simple_match = re.match(re.escape(entities["file_variable"]) + r"\.read\(\)", action_str)
            if action_assign_read_match: entities["file_action"] = {"type": "read_assign", "assign_to_var": action_assign_read_match.group(1).strip()}
            elif action_write_match: entities["file_action"] = {"type": "write", "write_expression": action_write_match.group(1).strip()}
            elif action_read_simple_match: entities["file_action"] = {"type": "read_expr"}
            else: entities["file_action"] = {"type": "unknown", "raw": action_str}
            return "add_file_operation"
    return None

def parse_intent(user_text: str) -> dict:
    user_text_lower = user_text.lower()
    entities = {}

    # --- Top-level creations first ---
    match_create_script = re.search(r"(?:create|make|new) (?:a|new)?\s*script (?:named|called)?\s*([a-zA-Z0-9_.-]+?)(?:\.py)?", user_text_lower)
    if match_create_script:
        script_name = match_create_script.group(1); entities["script_name"] = script_name if script_name.endswith(".py") else script_name + ".py"
        return {"intent": "create_script", "entities": entities}

    match_create_class = re.search(r"(?:create|make|new) class\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+in\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?", user_text_lower)
    if match_create_class:
        entities["class_name"] = match_create_class.group(1).strip()
        if match_create_class.group(2): entities["target_script"] = match_create_class.group(2).strip() if match_create_class.group(2).strip().endswith(".py") else match_create_class.group(2).strip() + ".py"
        return {"intent": "create_class_statement", "entities": entities}

    match_add_function = re.search(r"(?:add|define) (?:a )?function (?:named|called)?\s*([a-zA-Z0-9_]+)\s*(?:\((.*?)\))?((?:\s+(?:to|in) (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?)", user_text_lower)
    if match_add_function:
        if not re.search(r"(?:in|to)\s+class\s+", user_text_lower.split(match_add_function.group(1))[0]):
            entities["function_name"] = match_add_function.group(1).strip()
            parameters_str = match_add_function.group(2)
            entities["parameters"] = [p.strip() for p in parameters_str.split(',') if p.strip()] if parameters_str is not None else []
            if match_add_function.group(4): entities["target_script"] = match_add_function.group(4).strip() if match_add_function.group(4).strip().endswith(".py") else match_add_function.group(4).strip() + ".py"
            return {"intent": "add_function", "entities": entities}

    # --- Class Member Additions (method, instance attribute, class attribute) ---
    script_name_opt = None # To handle optional script name in these patterns
    match_add_method = None
    match_m_style1 = re.search(r"(?:in|to) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(?:add|define) method\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)", user_text_lower)
    if match_m_style1: match_add_method = match_m_style1; entities["class_name"] = match_m_style1.group(1).strip(); script_name_opt = match_m_style1.group(2); entities["method_name"] = match_m_style1.group(3).strip(); params_str_opt = match_m_style1.group(4)
    if not match_add_method:
        match_m_style2 = re.search(r"(?:add|define) method\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)\s*(?:to|in) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?", user_text_lower)
        if match_m_style2: match_add_method = match_m_style2; entities["method_name"] = match_m_style2.group(1).strip(); params_str_opt = match_m_style2.group(2); entities["class_name"] = match_m_style2.group(3).strip(); script_name_opt = match_m_style2.group(4)
    if match_add_method:
        if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"
        entities["parameters"] = [p.strip() for p in params_str_opt.split(',') if p.strip()] if params_str_opt is not None else []
        if not entities["parameters"] or entities["parameters"][0].lower() != "self": entities["parameters"].insert(0, "self")
        return {"intent": "add_method_to_class", "entities": entities}

    match_instance_attr = None; script_name_opt = None
    match_style_ia1 = re.search(r"(?:in|to) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?add instance attribute\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|initialized with)\s*(.+)", user_text_lower)
    if match_style_ia1: match_instance_attr = match_style_ia1; entities["class_name"] = match_style_ia1.group(1).strip(); script_name_opt = match_style_ia1.group(2); entities["attribute_name"] = match_style_ia1.group(3).strip(); entities["value_expression"] = match_style_ia1.group(4).strip()
    if not match_instance_attr:
        match_style_ia2 = re.search(r"add instance attribute\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|initialized with)\s*(.+?)\s*(?:to|in) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?", user_text_lower)
        if match_style_ia2: match_instance_attr = match_style_ia2; entities["attribute_name"] = match_style_ia2.group(1).strip(); entities["value_expression"] = match_style_ia2.group(2).strip(); entities["class_name"] = match_style_ia2.group(3).strip(); script_name_opt = match_style_ia2.group(4)
    if match_instance_attr and script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"
    if match_instance_attr:
        val_expr = entities["value_expression"]; is_literal = False
        try: ast.literal_eval(val_expr); is_literal = True
        except (ValueError, SyntaxError): pass
        if val_expr.isidentifier() and not is_literal: entities["init_param_suggestion"] = val_expr
        return {"intent": "add_instance_attribute", "entities": entities}

    match_add_class_attr = None; script_name_opt = None
    match_ca_style1 = re.search(r"(?:in|to) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?add (?:class )?attribute\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)", user_text_lower)
    if match_ca_style1: match_add_class_attr = match_ca_style1; entities["class_name"] = match_ca_style1.group(1).strip(); script_name_opt = match_ca_style1.group(2); entities["attribute_name"] = match_ca_style1.group(3).strip(); entities["value_expression"] = match_ca_style1.group(4).strip()
    if not match_add_class_attr:
        match_ca_style2 = re.search(r"add (?:class )?attribute\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+?)\s*(?:to|in) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?", user_text_lower)
        if match_ca_style2: match_add_class_attr = match_ca_style2; entities["attribute_name"] = match_ca_style2.group(1).strip(); entities["value_expression"] = match_ca_style2.group(2).strip(); entities["class_name"] = match_ca_style2.group(3).strip(); script_name_opt = match_ca_style2.group(4)
    if match_add_class_attr and script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"
    if match_add_class_attr: return {"intent": "add_class_attribute", "entities": entities}

    # --- Try-Except Block (potentially complex, handled before generic function body statements) ---
    # Regex: 1=method, 2=class_for_method, 3=function | 4=script | 5=try_body | 6=exc_type | 7=exc_var | 8=except_body
    match_try_except = re.search(
        r"in (?:method\s+([a-zA-Z0-9_]+)\s+of class\s+([a-zA-Z_][a-zA-Z0-9_]*)|function\s+([a-zA-Z0-9_]+))\s*"
        r"(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?"
        r"try\s*:\s*(.+?)\s*"
        r"except\s*(.*?)\s*" # Allow empty exception type
        r"(?:as\s+([a-zA-Z0-9_]+)\s*)?:\s*"
        r"(.+)",
        user_text_lower
    )
    if match_try_except:
        method_name = match_try_except.group(1); class_name_for_method = match_try_except.group(2); function_name = match_try_except.group(3)
        if method_name and class_name_for_method: entities["item_name"] = method_name; entities["class_name"] = class_name_for_method
        elif function_name: entities["item_name"] = function_name
        else: return {"intent": "unknown", "entities": {"error": "Target for try-except unclear."}}
        if match_try_except.group(4): entities["target_script"] = match_try_except.group(4).strip() if match_try_except.group(4).strip().endswith(".py") else match_try_except.group(4).strip() + ".py"
        entities["try_body_command_str"] = match_try_except.group(5).strip()
        entities["exception_type_str"] = match_try_except.group(6).strip()
        if not entities["exception_type_str"]: entities["exception_type_str"] = None # Bare except
        if match_try_except.group(7): entities["exception_as_variable"] = match_try_except.group(7).strip()
        entities["except_body_command_str"] = match_try_except.group(8).strip()
        entities["try_body_command_desc"] = parse_simple_body_command(entities["try_body_command_str"])
        entities["except_body_command_desc"] = parse_simple_body_command(entities["except_body_command_str"])
        return {"intent": "add_try_except", "entities": entities}

    # --- Contextual statements (print, return, if, for, while, file_op) within a function or method ---
    # Style 1: "in class C [in S] method M ..."
    match_in_method_context = re.search(r"in class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(?:method|in method)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(.*)", user_text_lower)
    if match_in_method_context:
        entities["class_name"] = match_in_method_context.group(1).strip()
        if match_in_method_context.group(2): entities["target_script"] = match_in_method_context.group(2).strip() if match_in_method_context.group(2).strip().endswith(".py") else match_in_method_context.group(2).strip() + ".py"
        entities["function_name"] = match_in_method_context.group(3).strip()
        remaining_command = match_in_method_context.group(4).strip()
        intent_from_body = parse_function_body_command_details(remaining_command, entities)
        if intent_from_body: return {"intent": intent_from_body, "entities": entities}
    else: # Style 2: "in method M of class C [in S] ..."
        match_in_method_context_alt = re.search(r"in method\s+([a-zA-Z0-9_]+)\s+of class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(.*)", user_text_lower)
        if match_in_method_context_alt:
            entities["function_name"] = match_in_method_context_alt.group(1).strip()
            entities["class_name"] = match_in_method_context_alt.group(2).strip()
            if match_in_method_context_alt.group(3): entities["target_script"] = match_in_method_context_alt.group(3).strip() if match_in_method_context_alt.group(3).strip().endswith(".py") else match_in_method_context_alt.group(3).strip() + ".py"
            remaining_command = match_in_method_context_alt.group(4).strip()
            intent_from_body = parse_function_body_command_details(remaining_command, entities)
            if intent_from_body: return {"intent": intent_from_body, "entities": entities}

    # Fallback: "in function F [in script S] ..." (global function context)
    match_in_function_context = re.search(r"in (?:function|method)\s+([a-zA-Z0-9_]+)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(.*)", user_text_lower)
    if match_in_function_context:
        entities["function_name"] = match_in_function_context.group(1).strip()
        if match_in_function_context.group(2): entities["target_script"] = match_in_function_context.group(2).strip() if match_in_function_context.group(2).strip().endswith(".py") else match_in_function_context.group(2).strip() + ".py"
        remaining_command = match_in_function_context.group(3).strip()
        intent_from_body = parse_function_body_command_details(remaining_command, entities)
        if intent_from_body: return {"intent": intent_from_body, "entities": entities}

    # --- Global statements ---
    match_from_import = re.search(r"from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_,\s]+)(?:\s+into\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?", user_text_lower)
    if match_from_import: # ... (logic as before)
        entities["import_type"] = "from_import"; entities["module"] = match_from_import.group(1).strip(); entities["names"] = [name.strip() for name in match_from_import.group(2).split(',') if name.strip()]
        if match_from_import.group(3): entities["target_script"] = match_from_import.group(3).strip() if match_from_import.group(3).strip().endswith(".py") else match_from_import.group(3).strip() + ".py"
        return {"intent": "add_import_statement", "entities": entities}

    match_direct_import = re.search(r"import\s+([a-zA-Z0-9_,\s]+)(?:\s+into\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?", user_text_lower)
    if match_direct_import: # ... (logic as before)
        from_keyword_present_before = False; # ... (full check for 'from' before 'import')
        if not from_keyword_present_before:
            entities["import_type"] = "direct_import"; entities["modules"] = [mod.strip() for mod in match_direct_import.group(1).split(',') if mod.strip()]
            if match_direct_import.group(2): entities["target_script"] = match_direct_import.group(2).strip() if match_direct_import.group(2).strip().endswith(".py") else match_direct_import.group(2).strip() + ".py"
            return {"intent": "add_import_statement", "entities": entities}

    match_language = re.search(r"(?:use|with|in)\s+(python|javascript|java|c\+\+)", user_text_lower)
    if match_language:
        entities["language"] = match_language.group(1)
        return {"intent": "specify_language", "entities": entities}

    return {"intent": "unknown", "entities": {}}
