import re
import ast # For literal_eval in add_instance_attribute heuristic

def _parse_command_sequence(sequence_str: str) -> list: # Renamed from parse_simple_body_command for clarity
    command_descs = []
    if not sequence_str: return [{"type": "pass"}]
    individual_commands = re.split(r'\s+then\s+', sequence_str.strip())
    for cmd_str in individual_commands:
        cmd_str = cmd_str.strip()
        if not cmd_str: continue
        if cmd_str.lower() == "pass": command_descs.append({"type": "pass"}); continue
        match_assign = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)", cmd_str, re.IGNORECASE)
        if match_assign: command_descs.append({"type": "assign", "target": match_assign.group(1).strip(), "expression": match_assign.group(2).strip()}); continue
        match_return = re.match(r"return\s+(.+)", cmd_str, re.IGNORECASE)
        if match_return: command_descs.append({"type": "return", "expression": match_return.group(1).strip()}); continue
        match_print = re.match(r"print\s+(.+)", cmd_str, re.IGNORECASE)
        if match_print: command_descs.append({"type": "print", "expression": match_print.group(1).strip()}); continue
        command_descs.append({"type": "unknown_statement", "raw_command": cmd_str})
    if not command_descs: return [{"type": "pass"}]
    return command_descs

def _parse_body_command_details_for_context(remaining_command: str, entities: dict, context_allows_file_op=True): # Renamed
    # This helper is for statements *after* "in function/method X" has been parsed
    # File op needs to be checked first due to its "then" keyword.
    if context_allows_file_op:
        match_file_op_body = re.match(r"open\s+(['\"].+?['\"])\s+for\s+(reading|writing|appending)\s+as\s+([a-zA-Z0-9_]+)\s+then\s+(.+)", remaining_command, re.IGNORECASE)
        if match_file_op_body:
            entities["filename"] = match_file_op_body.group(1).strip(); mode_str = match_file_op_body.group(2).strip().lower(); mode_map = {"reading": "r", "writing": "w", "appending": "a"}; entities["file_mode"] = mode_map.get(mode_str, "r")
            entities["file_variable"] = match_file_op_body.group(3).strip(); action_str = match_file_op_body.group(4).strip()
            action_assign_read_match = re.match(r"([a-zA-Z0-9_]+)\s*=\s*" + re.escape(entities["file_variable"]) + r"\.read\(\)", action_str, re.IGNORECASE)
            action_write_match = re.match(re.escape(entities["file_variable"]) + r"\.write\((.+)\)", action_str, re.IGNORECASE)
            action_read_simple_match = re.match(re.escape(entities["file_variable"]) + r"\.read\(\)", action_str, re.IGNORECASE)
            if action_assign_read_match: entities["file_action"] = {"type": "read_assign", "assign_to_var": action_assign_read_match.group(1).strip()}
            elif action_write_match: entities["file_action"] = {"type": "write", "write_expression": action_write_match.group(1).strip()}
            elif action_read_simple_match: entities["file_action"] = {"type": "read_expr"}
            else: entities["file_action"] = {"type": "unknown", "raw": action_str}
            return "add_file_operation"

    match_if = re.match(r"if\s+(.+?)\s+then\s+(.+?)(?:\s+else\s+(.+))?$", remaining_command, re.IGNORECASE | re.DOTALL)
    if match_if:
        entities["if_condition"] = match_if.group(1).strip(); entities["if_body_command_descs"] = _parse_command_sequence(match_if.group(2).strip())
        if match_if.group(3):
            else_elif_block = match_if.group(3).strip(); entities["elif_clauses"] = []
            while else_elif_block.lower().startswith("elif"):
                elif_match_inner = re.match(r"elif\s+(.+?)\s+then\s+(.+?)(\s*(?:elif.+|else.+))?$", else_elif_block, re.IGNORECASE | re.DOTALL)
                if elif_match_inner:
                    entities["elif_clauses"].append({"condition": elif_match_inner.group(1).strip(), "body_command_descs": _parse_command_sequence(elif_match_inner.group(2).strip())})
                    else_elif_block = elif_match_inner.group(3);
                    if else_elif_block: else_elif_block = else_elif_block.strip()
                    else: break
                else: break
            if else_elif_block: entities["else_body_command_descs"] = _parse_command_sequence(else_elif_block)
            else: entities["else_body_command_descs"] = None
        else: entities["else_body_command_descs"] = None; entities["elif_clauses"] = []
        return "add_conditional_statement"

    match_for = re.match(r"for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+(.+?)\s*:\s*(.+)", remaining_command, re.IGNORECASE | re.DOTALL)
    if match_for: entities["loop_variable"] = match_for.group(1).strip(); entities["iterable_expression"] = match_for.group(2).strip(); entities["body_command_descs"] = _parse_command_sequence(match_for.group(3).strip()); return "add_for_loop"
    match_while = re.match(r"while\s+(.+?)\s*:\s*(.+)", remaining_command, re.IGNORECASE | re.DOTALL)
    if match_while: entities["condition_expression"] = match_while.group(1).strip(); entities["body_command_descs"] = _parse_command_sequence(match_while.group(2).strip()); return "add_while_loop"

    # Simple print/return as single commands in a function/method body
    single_cmd_list = _parse_command_sequence(remaining_command) # Will be a list of one if simple
    if len(single_cmd_list) == 1:
        single_cmd_desc = single_cmd_list[0]
        if single_cmd_desc["type"] == "print": entities["expression"] = single_cmd_desc["expression"]; return "add_print_statement"
        if single_cmd_desc["type"] == "return": entities["expression"] = single_cmd_desc["expression"]; return "add_return_statement"
        # "assign" or "pass" are not typically "added" as a single operation this way, but are parts of other bodies.
        # If they become single operations, their intents would be handled here too.
    return None

def parse_intent(user_text: str) -> dict:
    user_text_lower = user_text.lower()
    entities = {}; script_name_opt = None

    # --- Top-level creations first ---
    match_create_script = re.search(r"(?:create|make|new) (?:a|new)?\s*script (?:named|called)?\s*([a-zA-Z0-9_.-]+?)(?:\.py)?", user_text_lower, re.IGNORECASE)
    if match_create_script: script_name = match_create_script.group(1); entities["script_name"] = script_name if script_name.endswith(".py") else script_name + ".py"; return {"intent": "create_script", "entities": entities}

    match_create_class = re.search(r"(?:create|make|new) class\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+in\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?", user_text_lower, re.IGNORECASE)
    if match_create_class: entities["class_name"] = match_create_class.group(1).strip(); script_name_opt = match_create_class.group(2); \
                           if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"; \
                           return {"intent": "create_class_statement", "entities": entities}

    # --- Add Method to Class (with optional multi-statement body) ---
    match_add_method = None; params_str_opt = ""; body_sequence_str = None
    m_style1 = re.search(r"(?:in|to) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(?:add|define) method\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)(?:\s*:\s*(.+))?", user_text_lower, re.IGNORECASE | re.DOTALL)
    if m_style1: match_add_method = m_style1; entities["class_name"] = m_style1.group(1).strip(); script_name_opt = m_style1.group(2); entities["method_name"] = m_style1.group(3).strip(); params_str_opt = m_style1.group(4); body_sequence_str = m_style1.group(5)
    if not match_add_method:
        m_style2 = re.search(r"(?:add|define) method\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)\s*(?:to|in) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(?:\s*:\s*(.+))?", user_text_lower, re.IGNORECASE | re.DOTALL)
        if m_style2: match_add_method = m_style2; entities["method_name"] = m_style2.group(1).strip(); params_str_opt = m_style2.group(2); entities["class_name"] = m_style2.group(3).strip(); script_name_opt = m_style2.group(4); body_sequence_str = m_style2.group(5)
    if match_add_method:
        if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"
        entities["parameters"] = [p.strip() for p in params_str_opt.split(',') if p.strip()] if params_str_opt is not None else []
        if not entities["parameters"] or entities["parameters"][0].lower() != "self": entities["parameters"].insert(0, "self")
        entities["body_command_descs"] = _parse_command_sequence(body_sequence_str.strip()) if body_sequence_str else [{"type": "pass"}]
        return {"intent": "add_method_to_class", "entities": entities}

    # --- Add Top-Level Function (no body parsing here, body added by subsequent commands) ---
    match_add_function = re.search(r"(?:add|define) (?:a )?function (?:named|called)?\s*([a-zA-Z0-9_]+)\s*(?:\((.*?)\))?((?:\s+(?:to|in) (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?)", user_text_lower, re.IGNORECASE)
    if match_add_function:
        if not re.search(r"(?:in|to)\s+class\s+", user_text_lower.split(match_add_function.group(1))[0]): # Avoid clash with method
            entities["function_name"] = match_add_function.group(1).strip(); parameters_str = match_add_function.group(2)
            entities["parameters"] = [p.strip() for p in parameters_str.split(',') if p.strip()] if parameters_str is not None else []
            if match_add_function.group(4): entities["target_script"] = match_add_function.group(4).strip() if match_add_function.group(4).strip().endswith(".py") else match_add_function.group(4).strip() + ".py"
            return {"intent": "add_function", "entities": entities}

    # --- Class Attribute Additions (instance, class) ---
    # ... (Instance and class attribute NLU as before, ensuring script_name_opt is handled) ...
    match_instance_attr = None; script_name_opt = None
    match_style_ia1 = re.search(r"(?:in|to) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?add instance attribute\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|initialized with)\s*(.+)", user_text_lower, re.IGNORECASE)
    if match_style_ia1: match_instance_attr = match_style_ia1; entities["class_name"] = match_style_ia1.group(1).strip(); script_name_opt = match_style_ia1.group(2); entities["attribute_name"] = match_style_ia1.group(3).strip(); entities["value_expression"] = match_style_ia1.group(4).strip()
    if not match_instance_attr:
        match_style_ia2 = re.search(r"add instance attribute\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|initialized with)\s*(.+?)\s*(?:to|in) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?", user_text_lower, re.IGNORECASE)
        if match_style_ia2: match_instance_attr = match_style_ia2; entities["attribute_name"] = match_style_ia2.group(1).strip(); entities["value_expression"] = match_style_ia2.group(2).strip(); entities["class_name"] = match_style_ia2.group(3).strip(); script_name_opt = match_style_ia2.group(4)
    if match_instance_attr and script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"
    if match_instance_attr:
        val_expr = entities["value_expression"]; is_literal = False
        try: ast.literal_eval(val_expr); is_literal = True
        except (ValueError, SyntaxError): pass
        if val_expr.isidentifier() and not is_literal: entities["init_param_suggestion"] = val_expr
        return {"intent": "add_instance_attribute", "entities": entities}

    match_add_class_attr = None; script_name_opt = None
    match_ca_style1 = re.search(r"(?:in|to) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?add (?:class )?attribute\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)", user_text_lower, re.IGNORECASE)
    if match_ca_style1: match_add_class_attr = match_ca_style1; entities["class_name"] = match_ca_style1.group(1).strip(); script_name_opt = match_ca_style1.group(2); entities["attribute_name"] = match_ca_style1.group(3).strip(); entities["value_expression"] = match_ca_style1.group(4).strip()
    if not match_add_class_attr:
        match_ca_style2 = re.search(r"add (?:class )?attribute\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+?)\s*(?:to|in) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?", user_text_lower, re.IGNORECASE)
        if match_ca_style2: match_add_class_attr = match_ca_style2; entities["attribute_name"] = match_ca_style2.group(1).strip(); entities["value_expression"] = match_ca_style2.group(2).strip(); entities["class_name"] = match_ca_style2.group(3).strip(); script_name_opt = match_ca_style2.group(4)
    if match_add_class_attr and script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"
    if match_add_class_attr: return {"intent": "add_class_attribute", "entities": entities}

    # --- Add Decorator ---
    chosen_match_decorator = None; script_name_str_decorator = None # Specific to avoid scope clash
    # Groups: 1=decorator_expression, 2=method_name, 3=class_name, 4=function_name, 5=script_name
    match_decorator_style1 = re.search(r"add decorator\s+@([a-zA-Z0-9_().,'\"=\s/\[\]\{\}:-]+)\s+to (?:method\s+([a-zA-Z0-9_]+)\s+in class\s+([a-zA-Z_][a-zA-Z0-9_]*)|function\s+([a-zA-Z0-9_]+))\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?", user_text_lower, re.IGNORECASE)
    if match_decorator_style1: chosen_match_decorator = match_decorator_style1; decorator_expr_str = chosen_match_decorator.group(1).strip(); method_name = chosen_match_decorator.group(2); class_name_for_method = chosen_match_decorator.group(3); function_name = chosen_match_decorator.group(4); script_name_str_decorator = chosen_match_decorator.group(5)
    if not chosen_match_decorator:
        match_decorator_style2 = re.search(r"decorate (?:method\s+([a-zA-Z0-9_]+)\s+in class\s+([a-zA-Z_][a-zA-Z0-9_]*)|function\s+([a-zA-Z0-9_]+))\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?with\s+@([a-zA-Z0-9_().,'\"=\s/\[\]\{\}:-]+)", user_text_lower, re.IGNORECASE)
        if match_decorator_style2: chosen_match_decorator = match_decorator_style2; method_name = match_decorator_style2.group(1); class_name_for_method = match_decorator_style2.group(2); function_name = match_decorator_style2.group(3); script_name_str_decorator = match_decorator_style2.group(4); decorator_expr_str = match_decorator_style2.group(5).strip()
    if not chosen_match_decorator:
        match_decorator_style3 = re.search(r"to (?:method\s+([a-zA-Z0-9_]+)\s+in class\s+([a-zA-Z_][a-zA-Z0-9_]*)|function\s+([a-zA-Z0-9_]+))\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?add decorator\s+@([a-zA-Z0-9_().,'\"=\s/\[\]\{\}:-]+)", user_text_lower, re.IGNORECASE)
        if match_decorator_style3: chosen_match_decorator = match_decorator_style3; method_name = match_decorator_style3.group(1); class_name_for_method = match_decorator_style3.group(2); function_name = match_decorator_style3.group(3); script_name_str_decorator = match_decorator_style3.group(4); decorator_expr_str = match_decorator_style3.group(5).strip()
    if chosen_match_decorator:
        if method_name and class_name_for_method: entities["item_name"] = method_name.strip(); entities["class_name"] = class_name_for_method.strip()
        elif function_name: entities["item_name"] = function_name.strip()
        else: return {"intent": "unknown", "entities": {"error": "Target for decorator unclear."}}
        if script_name_str_decorator: script_name = script_name_str_decorator.strip(); entities["target_script"] = script_name if script_name.endswith(".py") else script_name + ".py"
        entities["decorator_expression"] = decorator_expr_str; return {"intent": "add_decorator", "entities": entities}

    # --- Try-Except Block (captures multi-statement bodies, includes optional else/finally) ---
    match_try_except_core = re.search(r"in (?:method\s+([a-zA-Z0-9_]+)\s+of class\s+([a-zA-Z_][a-zA-Z0-9_]*)|function\s+([a-zA-Z0-9_]+))\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?try\s*:\s*(.+?)\s*except\s*(.*?)\s*(?:as\s+([a-zA-Z0-9_]+)\s*)?:\s*(.+?)(\s*(?:else\s*:\s*(.+?))?(\s*finally\s*:\s*(.+))?)?$", user_text_lower, re.IGNORECASE | re.DOTALL)
    if match_try_except_core: # ... (logic as before)
        method_name = match_try_except_core.group(1); class_name_for_method = match_try_except_core.group(2); function_name = match_try_except_core.group(3)
        if method_name and class_name_for_method: entities["item_name"] = method_name; entities["class_name"] = class_name_for_method
        elif function_name: entities["item_name"] = function_name
        else: return {"intent": "unknown", "entities": {"error": "Target for try-except unclear."}}
        if match_try_except_core.group(4): entities["target_script"] = match_try_except_core.group(4).strip() if match_try_except_core.group(4).strip().endswith(".py") else match_try_except_core.group(4).strip() + ".py"
        entities["try_body_command_descs"] = _parse_command_sequence(match_try_except_core.group(5).strip())
        exception_type = match_try_except_core.group(6).strip(); entities["exception_type_str"] = exception_type if exception_type else None
        if match_try_except_core.group(7): entities["exception_as_variable"] = match_try_except_core.group(7).strip()
        entities["except_body_command_descs"] = _parse_command_sequence(match_try_except_core.group(8).strip())
        optional_else_clause_str = match_try_except_core.group(10); optional_finally_clause_str = match_try_except_core.group(11)
        if optional_else_clause_str: entities["else_body_command_descs"] = _parse_command_sequence(optional_else_clause_str.strip())
        if optional_finally_clause_str: entities["finally_body_command_descs"] = _parse_command_sequence(optional_finally_clause_str.strip())
        return {"intent": "add_try_except", "entities": entities}

    # --- Contextual statements (if, for, while, file_op, print, return) ---
    # Style 1: "in class C [in S] method M <COMMAND_DETAILS>"
    match_in_method_context = re.search(r"in class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(?:method|in method)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(.*)", user_text_lower, re.IGNORECASE | re.DOTALL)
    if not match_in_method_context: # Style 2: "in method M of class C [in S] <COMMAND_DETAILS>"
        match_in_method_context = re.search(r"in method\s+([a-zA-Z0-9_]+)\s+of class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(.*)", user_text_lower, re.IGNORECASE | re.DOTALL)
        if match_in_method_context: entities["function_name"] = match_in_method_context.group(1).strip(); entities["class_name"] = match_in_method_context.group(2).strip(); script_name_opt = match_in_method_context.group(3); remaining_command = match_in_method_context.group(4).strip()
    elif style1_method_context: # Matched Style 1
        entities["class_name"] = match_in_method_context.group(1).strip(); script_name_opt = match_in_method_context.group(2); entities["function_name"] = match_in_method_context.group(3).strip(); remaining_command = match_in_method_context.group(4).strip()

    if match_in_method_context: # If any method context matched
        if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"
        intent_from_body = _parse_body_command_details_for_context(remaining_command, entities)
        if intent_from_body: return {"intent": intent_from_body, "entities": entities}

    # Fallback: "in function F [in S] <COMMAND_DETAILS>" (global function context)
    match_in_function_context = re.search(r"in (?:function|method)\s+([a-zA-Z0-9_]+)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(.*)", user_text_lower, re.IGNORECASE | re.DOTALL)
    if match_in_function_context:
        entities["function_name"] = match_in_function_context.group(1).strip(); script_name_opt = match_in_function_context.group(2)
        if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"
        remaining_command = match_in_function_context.group(3).strip()
        intent_from_body = _parse_body_command_details_for_context(remaining_command, entities)
        if intent_from_body: return {"intent": intent_from_body, "entities": entities}

    # --- Global statements (imports, language) ---
    # ... (import and language regexes as before, ensuring they are the last structural checks)
    match_from_import = re.search(r"from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_,\s]+)(?:\s+into\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?", user_text_lower, re.IGNORECASE)
    if match_from_import: entities["import_type"] = "from_import"; entities["module"] = match_from_import.group(1).strip(); entities["names"] = [name.strip() for name in match_from_import.group(2).split(',') if name.strip()]; script_name_opt=match_from_import.group(3); \
                           if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"; \
                           return {"intent": "add_import_statement", "entities": entities}
    match_direct_import = re.search(r"import\s+([a-zA-Z0-9_,\s]+)(?:\s+into\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?", user_text_lower, re.IGNORECASE)
    if match_direct_import: # ... (logic to avoid "from ... import" conflict)
        from_keyword_present_before = False; # ... (full check for 'from' before 'import')
        if not from_keyword_present_before:
            entities["import_type"] = "direct_import"; entities["modules"] = [mod.strip() for mod in match_direct_import.group(1).split(',') if mod.strip()]; script_name_opt=match_direct_import.group(2); \
            if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"; \
            return {"intent": "add_import_statement", "entities": entities}
    match_language = re.search(r"(?:use|with|in)\s+(python|javascript|java|c\+\+)", user_text_lower, re.IGNORECASE)
    if match_language: entities["language"] = match_language.group(1); return {"intent": "specify_language", "entities": entities}

    return {"intent": "unknown", "entities": {}}
