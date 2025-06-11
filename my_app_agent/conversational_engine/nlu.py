import re
import ast
import keyword # Added for _smart_format_item

def _smart_format_item(item_str: str) -> str:
    item_str = item_str.strip()
    # Check if it's already a valid string literal
    if (item_str.startswith("'") and item_str.endswith("'")) or \
       (item_str.startswith('"') and item_str.endswith('"')):
        return item_str
    if (item_str.startswith("f'") and item_str.endswith("'")) or \
       (item_str.startswith('f"') and item_str.endswith('"')): # f-strings
        return item_str

    # Check for Python literals (True, False, None)
    if item_str.lower() == "true": return "True"
    if item_str.lower() == "false": return "False"
    if item_str.lower() == "none": return "None"

    # Check if it's a number (integer or float)
    try:
        float(item_str) # This will also validate integers
        return item_str # Return as is, if it's a number
    except ValueError:
        pass # Not a number

    # Check if it's a valid identifier (potential variable name) and not a keyword
    if item_str.isidentifier() and not keyword.iskeyword(item_str):
        return item_str

    # Default: treat as a string literal (add quotes)
    # Escape existing single quotes if we are using single quotes
    escaped_item_str = item_str.replace("'", "\\'")
    return f"'{escaped_item_str}'"

def _parse_list_content_str(content_str: str) -> str:
    # Split by comma, and also "and" potentially preceded/followed by comma
    items = re.split(r'\s*,\s*and\s+|\s+and\s+|\s*,\s*', content_str)
    formatted_items = [_smart_format_item(item) for item in items if item.strip()]
    return f"[{', '.join(formatted_items)}]"

def _parse_dict_content_str(content_str: str) -> str:
    # Iteratively find "key K value V" pairs, allowing "and" or "," as separators
    # This regex is complex:
    # (?:key\s+)? : optionally matches "key "
    # (['"a-zA-Z_][a-zA-Z0-9_]*) : captures the key (group 1), allowing quoted or unquoted simple keys
    # \s+(?:is|value|is value|value is|=)\s*: matches separators like "is", "value", "=", etc.
    # (.+?) : captures the value (group 2), non-greedy
    # (?=\s+and\s+key\s|\s+key\s|$) : positive lookahead for " and key ", " key ", or end of string
    # This lookahead helps delimit the value part correctly.

    # Simplified: Assume "key K value V" and "and" as primary separator
    # For "key name value user_name and key id value 123"
    # First split by " and " or ", " if they separate full K-V pairs

    # Let's try a simpler split by "and" for K-V pairs, then parse each.
    # This assumes "key K value V" is the main structure for each pair.
    pair_strs = re.split(r'\s+and\s+(?=key\s)', content_str, flags=re.IGNORECASE) # Split by "and" only if followed by "key"

    dict_items = []
    for pair_str in pair_strs:
        pair_str = pair_str.strip()
        # Regex for "key K value V" or "K:V" or "K is V"
        # Groups: 1=key, 2=value after "value" or "is", 3=value after ":"
        match = re.match(r"(?:key\s+)?(['\"a-zA-Z_][a-zA-Z0-9_]*)\s+(?:value|is|=)\s+(.+)", pair_str, re.IGNORECASE)
        if not match: # Try colon format e.g. "'name': 'John Doe'"
             match = re.match(r"(['\"a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.+)", pair_str, re.IGNORECASE)
             if match: # Key is group 1, Value is group 2 for colon format
                 key_part = match.group(1).strip()
                 value_part = match.group(2).strip()
             else: continue # Skip if malformed
        else: # Key is group 1, Value is group 2 for "key K value V" format
            key_part = match.group(1).strip()
            value_part = match.group(2).strip()

        key_str = _smart_format_item(key_part)
        # Ensure dictionary keys that are simple names become strings
        if key_str.isidentifier() and not (key_str.startswith("'") or key_str.startswith('"')):
            key_str = f"'{key_str}'"

        value_str = _smart_format_item(value_part)
        dict_items.append(f"{key_str}: {value_str}")

    return f"{{{', '.join(dict_items)}}}"


def _parse_expression_string_for_literals(expression_str: str) -> str:
    """
    Checks if the expression_str matches list or dict patterns.
    If so, returns the formatted Python literal string. Otherwise, original string.
    """
    expression_str_lower = expression_str.lower()

    # List detection: "a list of X, Y, Z" or "list X, Y and Z" or "[X, Y, Z]" (already literal)
    # More flexible: "list items X, Y, Z", "list with X and Y"
    match_list = re.match(r"(?:a |the )?list (?:of |containing |with |items )?(.+)", expression_str_lower)
    if match_list:
        list_content = expression_str[match_list.start(1):match_list.end(1)] # Get original case content
        return _parse_list_content_str(list_content)

    # Dictionary detection: "a dict with key K value V and key K2 value V2"
    # or "dictionary key K is V, key K2: V2"
    match_dict = re.match(r"(?:a |the )?dict(?:ionary)? (?:with |of |map |mapping )?(.+)", expression_str_lower)
    if match_dict:
        dict_content = expression_str[match_dict.start(1):match_dict.end(1)] # Original case
        return _parse_dict_content_str(dict_content)

    return expression_str # Original if no list/dict pattern


def _parse_command_sequence(sequence_str: str) -> list:
    command_descs = []
    if not sequence_str: return [{"type": "pass"}]
    individual_commands = re.split(r'\s+then\s+', sequence_str.strip())
    for cmd_str in individual_commands:
        cmd_str = cmd_str.strip()
        if not cmd_str: continue
        if cmd_str.lower() == "pass": command_descs.append({"type": "pass"}); continue

        match_assign = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)", cmd_str, re.IGNORECASE)
        if match_assign:
            raw_expr = match_assign.group(2).strip()
            parsed_expr = _parse_expression_string_for_literals(raw_expr)
            command_descs.append({"type": "assign", "target": match_assign.group(1).strip(), "expression": parsed_expr}); continue

        match_return = re.match(r"return\s+(.+)", cmd_str, re.IGNORECASE)
        if match_return:
            raw_expr = match_return.group(1).strip()
            parsed_expr = _parse_expression_string_for_literals(raw_expr)
            command_descs.append({"type": "return", "expression": parsed_expr}); continue

        match_print = re.match(r"print\s+(.+)", cmd_str, re.IGNORECASE)
        if match_print:
            raw_expr = match_print.group(1).strip()
            parsed_expr = _parse_expression_string_for_literals(raw_expr)
            command_descs.append({"type": "print", "expression": parsed_expr}); continue

        command_descs.append({"type": "unknown_statement", "raw_command": cmd_str})
    if not command_descs: return [{"type": "pass"}]
    return command_descs

def _parse_body_command_details_for_context(remaining_command: str, entities: dict, context_allows_file_op=True):
    # This function now primarily deals with complex statements (if, for, while, file_op, try_except)
    # as _parse_command_sequence handles sequences of simple statements (print, return, assign, pass).
    # Simple print/return at this level are single commands in a sequence.

    # Try-Except (Most complex, check first)
    # Groups: 1=try_body_seq, 2=exc_type, 3=(opt)exc_var, 4=exc_body_seq, 5=(opt)else_finally_block
    match_try_except = re.match(r"try\s*:\s*(.+?)\s*except\s*(.*?)\s*(?:as\s+([a-zA-Z0-9_]+)\s*)?:\s*(.+?)(\s*(?:else\s*:\s*.+?|finally\s*:\s*.+))?$", remaining_command, re.IGNORECASE | re.DOTALL)
    if match_try_except:
        entities["try_body_command_descs"] = _parse_command_sequence(match_try_except.group(1).strip())
        exception_type = match_try_except.group(2).strip(); entities["exception_type_str"] = exception_type if exception_type else None
        if match_try_except.group(3): entities["exception_as_variable"] = match_try_except.group(3).strip()
        entities["except_body_command_descs"] = _parse_command_sequence(match_try_except.group(4).strip())
        else_finally_block_str = match_try_except.group(5)
        if else_finally_block_str: # ... (parse else/finally as in main parse_intent)
            else_finally_block_str = else_finally_block_str.strip()
            match_else = re.match(r"else\s*:\s*(.+?)(\s*finally\s*:.*)?$", else_finally_block_str, re.IGNORECASE | re.DOTALL)
            if match_else: entities["else_body_command_descs"] = _parse_command_sequence(match_else.group(1).strip()); optional_clauses_str = match_else.group(2)
            else: optional_clauses_str = else_finally_block_str # No else, could be just finally
            if optional_clauses_str: optional_clauses_str = optional_clauses_str.strip()
            if optional_clauses_str and optional_clauses_str.lower().startswith("finally"):
                 match_finally = re.match(r"finally\s*:\s*(.+)$", optional_clauses_str, re.IGNORECASE | re.DOTALL)
                 if match_finally: entities["finally_body_command_descs"] = _parse_command_sequence(match_finally.group(1).strip())
        return "add_try_except"

    # Conditional
    match_if = re.match(r"if\s+(.+?)\s+then\s+(.+?)(?:\s+else\s+(.+))?$", remaining_command, re.IGNORECASE | re.DOTALL)
    if match_if:
        entities["if_condition"] = match_if.group(1).strip(); entities["if_body_command_descs"] = _parse_command_sequence(match_if.group(2).strip())
        if match_if.group(3):
            else_elif_block = match_if.group(3).strip(); entities["elif_clauses"] = []
            while else_elif_block.lower().startswith("elif"):
                elif_match_inner = re.match(r"elif\s+(.+?)\s+then\s+(.+?)(\s*(?:elif.+|else.+))?$", else_elif_block, re.IGNORECASE | re.DOTALL)
                if elif_match_inner: entities["elif_clauses"].append({"condition": elif_match_inner.group(1).strip(), "body_command_descs": _parse_command_sequence(elif_match_inner.group(2).strip())}); else_elif_block = elif_match_inner.group(3);
                else: break
                if else_elif_block: else_elif_block = else_elif_block.strip()
                else: break
            if else_elif_block: entities["else_body_command_descs"] = _parse_command_sequence(else_elif_block)
            else: entities["else_body_command_descs"] = None
        else: entities["else_body_command_descs"] = None; entities["elif_clauses"] = []
        return "add_conditional_statement"

    # Loops
    match_for = re.match(r"for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+(.+?)\s*:\s*(.+)", remaining_command, re.IGNORECASE | re.DOTALL)
    if match_for: entities["loop_variable"] = match_for.group(1).strip(); entities["iterable_expression"] = match_for.group(2).strip(); entities["body_command_descs"] = _parse_command_sequence(match_for.group(3).strip()); return "add_for_loop"
    match_while = re.match(r"while\s+(.+?)\s*:\s*(.+)", remaining_command, re.IGNORECASE | re.DOTALL)
    if match_while: entities["condition_expression"] = match_while.group(1).strip(); entities["body_command_descs"] = _parse_command_sequence(match_while.group(2).strip()); return "add_while_loop"

    # File Operation
    if context_allows_file_op: # ... (file_op logic as before)
        match_file_op_body = re.match(r"open\s+(['\"].+?['\"])\s+for\s+(reading|writing|appending)\s+as\s+([a-zA-Z0-9_]+)\s+then\s+(.+)", remaining_command, re.IGNORECASE)
        if match_file_op_body: # ... (populate entities for file_op)
            entities["filename"] = match_file_op_body.group(1).strip(); mode_str = match_file_op_body.group(2).strip().lower(); mode_map = {"reading": "r", "writing": "w", "appending": "a"}; entities["file_mode"] = mode_map.get(mode_str, "r")
            entities["file_variable"] = match_file_op_body.group(3).strip(); action_str = match_file_op_body.group(4).strip()
            action_assign_read_match = re.match(r"([a-zA-Z0-9_]+)\s*=\s*" + re.escape(entities["file_variable"]) + r"\.read\(\)", action_str, re.IGNORECASE) # ... (rest of file_action parsing)
            if action_assign_read_match: entities["file_action"] = {"type": "read_assign", "assign_to_var": action_assign_read_match.group(1).strip()}
            # ... (other file_action types)
            else: entities["file_action"] = {"type": "unknown", "raw": action_str}
            return "add_file_operation"

    # If it's not a complex structure, try parsing as a single simple command (print, return)
    # This is for cases like "in function foo print 'hello'" where "print 'hello'" is the remaining_command.
    single_cmd_list = _parse_command_sequence(remaining_command)
    if len(single_cmd_list) == 1 and single_cmd_list[0]["type"] != "unknown_statement":
        cmd_type = single_cmd_list[0]["type"]
        if cmd_type == "print": entities["expression"] = single_cmd_list[0]["expression"]; return "add_print_statement"
        if cmd_type == "return": entities["expression"] = single_cmd_list[0]["expression"]; return "add_return_statement"
        # Assign and Pass are not typically standalone intents in this direct context.
    return None

def parse_intent(user_text: str) -> dict: # Main NLU dispatcher
    user_text_lower = user_text.lower(); entities = {}; script_name_opt = None; params_str_opt = ""; body_sequence_str = None

    # --- Top-level creations & Global settings ---
    # ... (create_script, create_class_statement, add_function (top-level), add_import, specify_language - as before)
    match_create_script = re.search(r"(?:create|make|new) (?:a|new)?\s*script (?:named|called)?\s*([a-zA-Z0-9_.-]+?)(?:\.py)?", user_text_lower, re.IGNORECASE)
    if match_create_script: script_name = match_create_script.group(1); entities["script_name"] = script_name if script_name.endswith(".py") else script_name + ".py"; return {"intent": "create_script", "entities": entities}
    match_create_class = re.search(r"(?:create|make|new) class\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+in\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?", user_text_lower, re.IGNORECASE)
    if match_create_class: entities["class_name"] = match_create_class.group(1).strip(); script_name_opt = match_create_class.group(2); \
                           if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"; \
                           return {"intent": "create_class_statement", "entities": entities}
    match_add_function = re.search(r"(?:add|define) (?:a )?function (?:named|called)?\s*([a-zA-Z0-9_]+)\s*(?:\((.*?)\))?((?:\s+(?:to|in) (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?)", user_text_lower, re.IGNORECASE)
    if match_add_function:
        if not re.search(r"(?:in|to)\s+class\s+", user_text_lower.split(match_add_function.group(1))[0]):
            entities["function_name"] = match_add_function.group(1).strip(); parameters_str = match_add_function.group(2)
            entities["parameters"] = [p.strip() for p in parameters_str.split(',') if p.strip()] if parameters_str is not None else []
            if match_add_function.group(4): entities["target_script"] = match_add_function.group(4).strip() if match_add_function.group(4).strip().endswith(".py") else match_add_function.group(4).strip() + ".py"
            return {"intent": "add_function", "entities": entities}

    # --- Class Member Additions (method, attributes) ---
    # ... (add_method_to_class, add_instance_attribute, add_class_attribute - as before, but method now uses _parse_command_sequence for body)
    match_add_method = None;
    m_style1 = re.search(r"(?:in|to) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(?:add|define) method\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)(?:\s*:\s*(.+))?", user_text_lower, re.IGNORECASE | re.DOTALL)
    if m_style1: match_add_method = m_style1; entities["class_name"] = m_style1.group(1).strip(); script_name_opt = m_style1.group(2); entities["method_name"] = m_style1.group(3).strip(); params_str_opt = m_style1.group(4); body_sequence_str = m_style1.group(5)
    if not match_add_method: # ... (style 2 for add_method)
        m_style2 = re.search(r"(?:add|define) method\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)\s*(?:to|in) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(?:\s*:\s*(.+))?", user_text_lower, re.IGNORECASE | re.DOTALL)
        if m_style2: match_add_method = m_style2; entities["method_name"] = m_style2.group(1).strip(); params_str_opt = m_style2.group(2); entities["class_name"] = m_style2.group(3).strip(); script_name_opt = m_style2.group(4); body_sequence_str = m_style2.group(5)
    if match_add_method: # ... (process params, body_command_descs, return)
        if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"
        entities["parameters"] = [p.strip() for p in params_str_opt.split(',') if p.strip()] if params_str_opt is not None else []
        if not entities["parameters"] or entities["parameters"][0].lower() != "self": entities["parameters"].insert(0, "self")
        entities["body_command_descs"] = _parse_command_sequence(body_sequence_str.strip()) if body_sequence_str else [{"type": "pass"}]
        return {"intent": "add_method_to_class", "entities": entities}

    # ... (Instance and Class attribute NLU as before)

    # --- Try-Except Block (has its own comprehensive regex) ---
    # ... (Full try-except-else-finally regex from previous subtask, using _parse_command_sequence for bodies)
    match_try_except_core = re.search(r"in (?:method\s+([a-zA-Z0-9_]+)\s+of class\s+([a-zA-Z_][a-zA-Z0-9_]*)|function\s+([a-zA-Z0-9_]+))\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?try\s*:\s*(.+?)\s*except\s*(.*?)\s*(?:as\s+([a-zA-Z0-9_]+)\s*)?:\s*(.+?)(\s*(?:else\s*:\s*(.+?))?(\s*finally\s*:\s*(.+))?)?$", user_text_lower, re.IGNORECASE | re.DOTALL)
    if match_try_except_core: # ... (populate entities, including try/except/else/finally_body_command_descs using _parse_command_sequence)
        method_name = match_try_except_core.group(1); class_name_for_method = match_try_except_core.group(2); function_name = match_try_except_core.group(3)
        if method_name and class_name_for_method: entities["item_name"] = method_name; entities["class_name"] = class_name_for_method
        elif function_name: entities["item_name"] = function_name
        else: return {"intent": "unknown", "entities": {"error": "Target for try-except unclear."}}
        if match_try_except_core.group(4): entities["target_script"] = match_try_except_core.group(4).strip() if match_try_except_core.group(4).strip().endswith(".py") else match_try_except_core.group(4).strip() + ".py"
        entities["try_body_command_descs"] = _parse_command_sequence(match_try_except_core.group(5).strip())
        exception_type = match_try_except_core.group(6).strip(); entities["exception_type_str"] = exception_type if exception_type else None
        if match_try_except_core.group(7): entities["exception_as_variable"] = match_try_except_core.group(7).strip()
        entities["except_body_command_descs"] = _parse_command_sequence(match_try_except_core.group(8).strip())
        else_body_str = match_try_except_core.group(10); finally_body_str = match_try_except_core.group(11) # Adjusted group indices based on regex structure
        if else_body_str: entities["else_body_command_descs"] = _parse_command_sequence(else_body_str.strip())
        if finally_body_str: entities["finally_body_command_descs"] = _parse_command_sequence(finally_body_str.strip())
        return {"intent": "add_try_except", "entities": entities}


    # --- Contextual statements (if, for, while, file_op, print, return) ---
    # ... (Using the refactored structure with _parse_body_command_details_for_context)
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

    match_in_function_context = re.search(r"in (?:function|method)\s+([a-zA-Z0-9_]+)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(.*)", user_text_lower, re.IGNORECASE | re.DOTALL)
    if match_in_function_context:
        entities["function_name"] = match_in_function_context.group(1).strip(); script_name_opt = match_in_function_context.group(2)
        if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"
        remaining_command = match_in_function_context.group(3).strip()
        intent_from_body = _parse_body_command_details_for_context(remaining_command, entities)
        if intent_from_body: return {"intent": intent_from_body, "entities": entities}

    # --- Global statements (imports, language) ---
    # ... (as before)
    match_from_import = re.search(r"from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_,\s]+)(?:\s+into\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?", user_text_lower, re.IGNORECASE)
    if match_from_import: entities["import_type"] = "from_import"; entities["module"] = match_from_import.group(1).strip(); entities["names"] = [name.strip() for name in match_from_import.group(2).split(',') if name.strip()]; script_name_opt=match_from_import.group(3); \
                           if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"; \
                           return {"intent": "add_import_statement", "entities": entities}
    match_direct_import = re.search(r"import\s+([a-zA-Z0-9_,\s]+)(?:\s+into\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?", user_text_lower, re.IGNORECASE)
    if match_direct_import: # ... (logic to avoid "from ... import" conflict)
        from_keyword_present_before = False;
        if not from_keyword_present_before:
            entities["import_type"] = "direct_import"; entities["modules"] = [mod.strip() for mod in match_direct_import.group(1).split(',') if mod.strip()]; script_name_opt=match_direct_import.group(2); \
            if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"; \
            return {"intent": "add_import_statement", "entities": entities}
    match_language = re.search(r"(?:use|with|in)\s+(python|javascript|java|c\+\+)", user_text_lower, re.IGNORECASE)
    if match_language: entities["language"] = match_language.group(1); return {"intent": "specify_language", "entities": entities}

    return {"intent": "unknown", "entities": {}}
