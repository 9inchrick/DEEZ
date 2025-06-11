import re
import ast 
import keyword 

def _smart_format_item(item_str: str, for_fstring_literal_part=False) -> str:
    item_str = item_str.strip()
    if (item_str.startswith("'") and item_str.endswith("'")) or \
       (item_str.startswith('"') and item_str.endswith('"')):
        if for_fstring_literal_part: # Inside f-string, use inner content, escape braces
            return item_str[1:-1].replace('{', '{{').replace('}', '}}')
        return item_str # As a standalone item, keep quotes
    if (item_str.startswith("f'") and item_str.endswith("'")) or \
       (item_str.startswith('f"') and item_str.endswith('"')): # Already an f-string
        if for_fstring_literal_part: # This is complex, f-string within f-string literal part
             # For now, treat as literal, escape its special chars.
             # A true nested f-string would be f"foo{f'bar'}" which is fine.
             # This case is if user said "f-string 'hello' then f'world {var}'"
             # The f'world {var}' part needs to be added carefully.
             # Simplest: treat as literal for now.
            return item_str.replace('{', '{{').replace('}', '}}')
        return item_str 

    if item_str.lower() == "true": return "True" if not for_fstring_literal_part else "True" # Or f"{True}"
    if item_str.lower() == "false": return "False" if not for_fstring_literal_part else "False"
    if item_str.lower() == "none": return "None" if not for_fstring_literal_part else "None"
    
    try: float(item_str); return item_str # Numbers are fine as is
    except ValueError: pass 
    
    if item_str.isidentifier() and not keyword.iskeyword(item_str):
        return item_str # Variable name
    
    if for_fstring_literal_part: # Part of an f-string literal text
        return item_str.replace('{', '{{').replace('}', '}}')
    else: # Default: treat as a string literal for lists/dicts
        return f"'{item_str.replace('\"', '\\\"').replace(\"'\", \"\\'\")}'"


def _parse_list_content_str(content_str: str) -> str: 
    items = re.split(r'\s*,\s*and\s+|\s+and\s+|\s*,\s*', content_str)
    formatted_items = [_smart_format_item(item) for item in items if item.strip()]
    return f"[{', '.join(formatted_items)}]"

def _parse_dict_content_str(content_str: str) -> str: 
    pair_strs = re.split(r'\s+and\s+(?=key\s|[\'"][a-zA-Z0-9_]+[\'"]\s*:)', content_str, flags=re.IGNORECASE) 
    dict_items = []
    for pair_str in pair_strs:
        pair_str = pair_str.strip()
        match = re.match(r"(?:key\s+)?(['\"a-zA-Z_][a-zA-Z0-9_]*)\s+(?:value|is|=)\s+(.+)", pair_str, re.IGNORECASE)
        if not match: match = re.match(r"(['\"a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.+)", pair_str, re.IGNORECASE)
        if match:
            key_part = match.group(1).strip(); value_part = match.group(2).strip()
            key_str = _smart_format_item(key_part)
            if key_str.isidentifier() and not (key_str.startswith("'") or key_str.startswith('"')): key_str = f"'{key_str}'"
            value_str = _smart_format_item(value_part)
            dict_items.append(f"{key_str}: {value_str}")
    return f"{{{', '.join(dict_items)}}}"

def _parse_f_string_content(content_str: str) -> str:
    parts = re.split(r'\s+then\s+', content_str.strip())
    processed_f_string_parts = []
    for p_str in parts:
        p_str = p_str.strip()
        if not p_str: continue

        # If it's an explicitly quoted string, treat its content as literal f-string text
        if (p_str.startswith("'") and p_str.endswith("'")) or \
           (p_str.startswith('"') and p_str.endswith('"')):
            processed_f_string_parts.append(p_str[1:-1].replace('{', '{{').replace('}', '}}'))
        # If it's a boolean or None literal, embed as {True}, {False}, {None}
        elif p_str.lower() in ["true", "false", "none"]:
            processed_f_string_parts.append(f"{{{p_str.capitalize()}}}") # Ensure correct casing
        else:
            try: # Is it a number? Embed as {number}
                float(p_str)
                processed_f_string_parts.append(f"{{{p_str}}}")
            except ValueError: # Not a number
                # Assume it's a variable or a more complex expression
                if (p_str.isidentifier() and not keyword.iskeyword(p_str)) or \
                   re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*\(.*\)$", p_str) or \
                   re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*(\.[a-zA-Z_][a-zA-Z0-9_]*)+$", p_str) or \
                   re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*\[.+\]$", p_str): # var, func(), var.attr, var[key]
                    processed_f_string_parts.append(f"{{{p_str}}}")
                else: # Fallback: treat as literal string part, escape braces
                    processed_f_string_parts.append(p_str.replace('{', '{{').replace('}', '}}'))
    
    return f'f"{ "".join(processed_f_string_parts) }"'


def _parse_expression_string_for_literals(expression_str: str) -> str: 
    expression_str_lower = expression_str.lower()
    # F-String detection (NEW)
    # Regex: 1=content_of_fstring
    match_fstring = re.match(r"^(?:an? f-?string|formatted string|fstring)\s*(?:saying|with|:|that is)?\s*(.+)$", expression_str, re.IGNORECASE)
    if match_fstring:
        fstring_content = match_fstring.group(1).strip()
        return _parse_f_string_content(fstring_content)

    match_list = re.match(r"(?:a |the )?list (?:of |containing |with |items )?(.+)", expression_str, re.IGNORECASE) 
    if match_list: list_content = expression_str[match_list.start(1):match_list.end(1)]; return _parse_list_content_str(list_content)
    match_dict = re.match(r"(?:a |the )?dict(?:ionary)? (?:with |of |map |mapping )?(.+)", expression_str, re.IGNORECASE) 
    if match_dict: dict_content = expression_str[match_dict.start(1):match_dict.end(1)]; return _parse_dict_content_str(dict_content)
    return expression_str 

def _parse_command_sequence(sequence_str: str) -> list: # ... (as before, uses _parse_expression_string_for_literals)
    # ... (implementation from previous step, ensure it calls _parse_expression_string_for_literals for expressions)
    command_descs = []
    if not sequence_str: return [{"type": "pass"}] 
    individual_commands = re.split(r'\s+then\s+', sequence_str.strip())
    for cmd_str in individual_commands:
        cmd_str = cmd_str.strip();
        if not cmd_str: continue
        if cmd_str.lower() == "pass": command_descs.append({"type": "pass"}); continue
        match_assign = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)", cmd_str, re.IGNORECASE)
        if match_assign: raw_expr = match_assign.group(2).strip(); parsed_expr = _parse_expression_string_for_literals(raw_expr); command_descs.append({"type": "assign", "target": match_assign.group(1).strip(), "expression": parsed_expr}); continue
        match_return = re.match(r"return\s+(.+)", cmd_str, re.IGNORECASE)
        if match_return: raw_expr = match_return.group(1).strip(); parsed_expr = _parse_expression_string_for_literals(raw_expr); command_descs.append({"type": "return", "expression": parsed_expr}); continue
        match_print = re.match(r"print\s+(.+)", cmd_str, re.IGNORECASE)
        if match_print: raw_expr = match_print.group(1).strip(); parsed_expr = _parse_expression_string_for_literals(raw_expr); command_descs.append({"type": "print", "expression": parsed_expr}); continue
        command_descs.append({"type": "unknown_statement", "raw_command": cmd_str})
    if not command_descs: return [{"type": "pass"}]
    return command_descs

def _parse_body_command_details_for_context(remaining_command: str, entities: dict, context_allows_file_op=True): # ... (as before)
    # ... (implementation from previous step)
    if context_allows_file_op:
        match_file_op_body = re.match(r"open\s+(['\"].+?['\"])\s+for\s+(reading|writing|appending)\s+as\s+([a-zA-Z0-9_]+)\s+then\s+(.+)", remaining_command, re.IGNORECASE)
        if match_file_op_body: # ... (populate entities for file_op)
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
    if match_if: # ... (as before, including elif parsing)
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
    match_for = re.match(r"for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+(.+?)\s*:\s*(.+)", remaining_command, re.IGNORECASE | re.DOTALL)
    if match_for: entities["loop_variable"] = match_for.group(1).strip(); entities["iterable_expression"] = match_for.group(2).strip(); entities["body_command_descs"] = _parse_command_sequence(match_for.group(3).strip()); return "add_for_loop"
    match_while = re.match(r"while\s+(.+?)\s*:\s*(.+)", remaining_command, re.IGNORECASE | re.DOTALL)
    if match_while: entities["condition_expression"] = match_while.group(1).strip(); entities["body_command_descs"] = _parse_command_sequence(match_while.group(2).strip()); return "add_while_loop"
    single_cmd_list = _parse_command_sequence(remaining_command) 
    if len(single_cmd_list) == 1 and single_cmd_list[0]["type"] != "unknown_statement":
        cmd_type = single_cmd_list[0]["type"]
        if cmd_type == "print": entities["expression"] = single_cmd_list[0]["expression"]; return "add_print_statement"
        if cmd_type == "return": entities["expression"] = single_cmd_list[0]["expression"]; return "add_return_statement"
    return None 

def parse_intent(user_text: str) -> dict: # Main NLU dispatcher
    # ... (All other intent parsing logic as established in previous steps, ensuring correct order)
    user_text_lower = user_text.lower(); entities = {}; script_name_opt = None; params_str_opt = ""; body_sequence_str = None
    match_create_script = re.search(r"(?:create|make|new) (?:a|new)?\s*script (?:named|called)?\s*([a-zA-Z0-9_.-]+?)(?:\.py)?", user_text_lower, re.IGNORECASE); # ... (rest of create_script)
    if match_create_script: script_name = match_create_script.group(1); entities["script_name"] = script_name if script_name.endswith(".py") else script_name + ".py"; return {"intent": "create_script", "entities": entities}
    match_create_class = re.search(r"(?:create|make|new) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\s*(?:inherits|from|extends|child of|inheriting|extending|based on)\s+([a-zA-Z0-9_.,\s]+?)\s*)?(?:\s+in\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?", user_text_lower, re.IGNORECASE); # ... (rest of create_class)
    if match_create_class: entities["class_name"] = match_create_class.group(1).strip(); base_classes_str = match_create_class.group(2); script_name_opt = match_create_class.group(3); entities["base_classes"] = [bc.strip() for bc in re.split(r'\s*,\s*|\s+and\s+', base_classes_str) if bc.strip()] if base_classes_str else []; \
                           if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"; \
                           return {"intent": "create_class_statement", "entities": entities}
    match_add_method = None; # ... (rest of add_method_to_class)
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
    match_add_function = re.search(r"(?:add|define) (?:a )?function (?:named|called)?\s*([a-zA-Z0-9_]+)\s*(?:\((.*?)\))?((?:\s+(?:to|in) (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?)?)", user_text_lower, re.IGNORECASE)
    if match_add_function: # ... (as before)
        if not re.search(r"(?:in|to)\s+class\s+", user_text_lower.split(match_add_function.group(1))[0]): # Avoid clash with method
            entities["function_name"] = match_add_function.group(1).strip(); parameters_str = match_add_function.group(2)
            entities["parameters"] = [p.strip() for p in parameters_str.split(',') if p.strip()] if parameters_str is not None else []
            if match_add_function.group(4): entities["target_script"] = match_add_function.group(4).strip() if match_add_function.group(4).strip().endswith(".py") else match_add_function.group(4).strip() + ".py"
            return {"intent": "add_function", "entities": entities}
    match_prop = None; script_name_opt = None; full_details_str = "" # Property parsing ... (as before)
    prop_style1 = re.search(r"(?:in|to)\s+class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(?:add|create|define)?\s*property\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*((?:(?:for|from|using|backed by)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*)?(?:(?:with|and|create|add)?\s*(?:getter|setter|deleter|readable|writeable|deletable)\s*)*(?:(?:initialized|init|defaults)\s+to\s*.+)?)?", user_text_lower, re.IGNORECASE)
    if prop_style1: match_prop = prop_style1; entities["class_name"] = prop_style1.group(1).strip(); script_name_opt = prop_style1.group(2); entities["property_name"] = prop_style1.group(3).strip(); full_details_str = prop_style1.group(4).strip() if prop_style1.group(4) else ""
    if not match_prop:
        prop_style2 = re.search(r"(?:add|create|define)?\s*property\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*((?:(?:for|from|using|backed by)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*)?)?(?:to|in)\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*((?:in\s+(?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(?:(?:with|and|create|add)?\s*(?:getter|setter|deleter|readable|writeable|deletable)\s*)*(?:(?:initialized|init|defaults)\s+to\s*.+)?)?", user_text_lower, re.IGNORECASE)
        if prop_style2: match_prop = prop_style2; entities["property_name"] = prop_style2.group(1).strip(); private_attr_part = prop_style2.group(2).strip() if prop_style2.group(2) else ""; entities["class_name"] = prop_style2.group(3).strip(); script_name_opt_in_details = prop_style2.group(5); details_part = prop_style2.group(4).strip() if prop_style2.group(4) else ""; full_details_str = (private_attr_part + " " + details_part).strip(); script_name_opt = script_name_opt_in_details
    if match_prop: # ... (process full_details_str for private_attr, getter/setter/deleter, init_val as before)
        if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"
        priv_attr_match = re.search(r"(?:for|from|using|backed by|for attribute|for private attribute)\s+([a-zA-Z_][a-zA-Z0-9_]*)", full_details_str, re.IGNORECASE)
        if priv_attr_match: entities["private_attribute_name"] = priv_attr_match.group(1).strip()
        else: entities["private_attribute_name"] = f"_{entities['property_name']}"
        entities["create_getter"] = True 
        if re.search(r"(?:with|and|create|add)\s+setter|writeable", full_details_str, re.IGNORECASE): entities["create_setter"] = True
        else: entities["create_setter"] = False
        if re.search(r"(?:with|and|create|add)\s+deleter|deletable", full_details_str, re.IGNORECASE): entities["create_deleter"] = True
        else: entities["create_deleter"] = False
        init_val_match = re.search(r"(?:initialized|init|defaults)\s+to\s+(.+?)(\s+with|\s+and\s+for|$)", full_details_str, re.IGNORECASE)
        if init_val_match:
            val_expr = init_val_match.group(1).strip(); entities["initial_value_for_init"] = val_expr
            is_literal = False; try: ast.literal_eval(val_expr); is_literal = True; except (ValueError, SyntaxError): pass
            if val_expr.isidentifier() and not is_literal and not keyword.iskeyword(val_expr): entities["init_param_suggestion_for_prop_attr"] = val_expr
        return {"intent": "add_property_to_class", "entities": entities}
    # ... (instance and class attribute NLU as before)
    match_instance_attr = None; script_name_opt = None # ... (full logic as before)
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
    match_add_class_attr = None; script_name_opt = None # ... (full logic for class attr as before)
    match_ca_style1 = re.search(r"(?:in|to) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?add (?:class )?attribute\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)", user_text_lower, re.IGNORECASE)
    if match_ca_style1: match_add_class_attr = match_ca_style1; entities["class_name"] = match_ca_style1.group(1).strip(); script_name_opt = match_ca_style1.group(2); entities["attribute_name"] = match_ca_style1.group(3).strip(); entities["value_expression"] = match_ca_style1.group(4).strip()
    if not match_add_class_attr:
        match_ca_style2 = re.search(r"add (?:class )?attribute\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+?)\s*(?:to|in) class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?", user_text_lower, re.IGNORECASE)
        if match_ca_style2: match_add_class_attr = match_ca_style2; entities["attribute_name"] = match_ca_style2.group(1).strip(); entities["value_expression"] = match_ca_style2.group(2).strip(); entities["class_name"] = match_ca_style2.group(3).strip(); script_name_opt = match_ca_style2.group(4)
    if match_add_class_attr and script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"
    if match_add_class_attr: return {"intent": "add_class_attribute", "entities": entities}
    
    # --- Try-Except Block --- (as before)
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
        optional_clauses_str = match_try_except_core.group(9) 
        if optional_clauses_str:
            optional_clauses_str = optional_clauses_str.strip()
            match_else = re.match(r"else\s*:\s*(.+?)(\s*finally\s*:.*)?$", optional_clauses_str, re.IGNORECASE | re.DOTALL)
            if match_else: entities["else_body_command_descs"] = _parse_command_sequence(match_else.group(1).strip()); optional_clauses_str = match_else.group(2)
            if optional_clauses_str: optional_clauses_str = optional_clauses_str.strip()
            if optional_clauses_str and optional_clauses_str.lower().startswith("finally"):
                 match_finally = re.match(r"finally\s*:\s*(.+)$", optional_clauses_str, re.IGNORECASE | re.DOTALL)
                 if match_finally: entities["finally_body_command_descs"] = _parse_command_sequence(match_finally.group(1).strip())
        return {"intent": "add_try_except", "entities": entities}
        
    # --- Contextual statements (if, for, while, file_op, print, return) ---
    # ... (Using the refactored structure with _parse_body_command_details_for_context)
    match_in_method_context = None; remaining_command = None
    style1_method_context = re.search(r"in class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(?:method|in method)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(.*)", user_text_lower, re.IGNORECASE | re.DOTALL)
    if style1_method_context: match_in_method_context = style1_method_context; entities["class_name"] = style1_method_context.group(1).strip(); script_name_opt = style1_method_context.group(2); entities["function_name"] = style1_method_context.group(3).strip(); remaining_command = style1_method_context.group(4).strip()
    else:
        style2_method_context = re.search(r"in method\s+([a-zA-Z0-9_]+)\s+of class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:in (?:script\s*)?([a-zA-Z0-9_.-]+?)(?:\.py)?\s*)?(.*)", user_text_lower, re.IGNORECASE | re.DOTALL)
        if style2_method_context: match_in_method_context = style2_method_context; entities["function_name"] = style2_method_context.group(1).strip(); entities["class_name"] = style2_method_context.group(2).strip(); script_name_opt = style2_method_context.group(3); remaining_command = style2_method_context.group(4).strip()
    if match_in_method_context: 
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
    if match_direct_import:
        from_keyword_present_before = False; 
        if "from " in user_text_lower:
            try: from_idx = user_text_lower.index("from "); import_idx = user_text_lower.index("import ") 
            except ValueError: pass 
            else: 
                if from_idx < import_idx and user_text_lower[from_idx:import_idx].count("import") == 0: from_keyword_present_before = True
        if not from_keyword_present_before:
            entities["import_type"] = "direct_import"; entities["modules"] = [mod.strip() for mod in match_direct_import.group(1).split(',') if mod.strip()]; script_name_opt=match_direct_import.group(2); \
            if script_name_opt: entities["target_script"] = script_name_opt.strip() if script_name_opt.strip().endswith(".py") else script_name_opt.strip() + ".py"; \
            return {"intent": "add_import_statement", "entities": entities}
    match_language = re.search(r"(?:use|with|in)\s+(python|javascript|java|c\+\+)", user_text_lower, re.IGNORECASE)
    if match_language: entities["language"] = match_language.group(1); return {"intent": "specify_language", "entities": entities}
        
    return {"intent": "unknown", "entities": {}}
