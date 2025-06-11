import ast
import os
import keyword

BASE_PYTHON_OUTPUT_DIR = os.path.join(os.path.expanduser('~'), 'Documents', 'MyAppAgent', 'generated_scripts', 'python')

def to_source(node):
    try:
        return ast.unparse(node)
    except AttributeError:
        print("ERROR: ast.unparse is not available. MyAppAgent requires Python 3.9+.")
        raise
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during AST unparsing: {e}")
        raise

def _ensure_base_dir_exists():
    """Ensures the base Python output directory exists."""
    os.makedirs(BASE_PYTHON_OUTPUT_DIR, exist_ok=True)

def create_new_script(script_name: str, initial_comment: str = None) -> str:
    """Creates a new Python script. Returns full script_path on success, raises FileExistsError if exists."""
    if not script_name.endswith(".py"): script_name += ".py"
    _ensure_base_dir_exists()
    script_path = os.path.join(BASE_PYTHON_OUTPUT_DIR, script_name)
    if os.path.exists(script_path): raise FileExistsError(f"Python script '{script_path}' already exists.")

    module_body = []
    if initial_comment:
        module_body.append(ast.Expr(value=ast.Constant(value=initial_comment)))
    if not module_body:
        module_body.append(ast.Pass())
    module_node = ast.Module(body=module_body, type_ignores=[])
    script_content = to_source(module_node)
    with open(script_path, "w") as f:
        f.write(script_content)
        if not script_content.endswith("\n") and script_content: f.write("\n")
        elif not script_content: f.write("\n")
    return script_path

def _read_and_parse_script(script_name: str) -> tuple[ast.Module | None, str | None, str | None]:
    """
    Helper to construct path, read and parse a script.
    Returns (module_node, full_script_path_or_None, error_message_or_None).
    """
    if not script_name.endswith(".py"): script_name += ".py"
    _ensure_base_dir_exists() # Ensure base dir exists before trying to access files within it
    script_path = os.path.join(BASE_PYTHON_OUTPUT_DIR, script_name)
    if not os.path.exists(script_path): return None, None, f"Error: Script '{script_path}' not found."
    with open(script_path, "r") as f: source_code = f.read()
    try:
        module_node = ast.parse(source_code, filename=script_path)
        return module_node, script_path, None
    except SyntaxError as e:
        return None, script_path, f"Error parsing script '{script_path}': {e}"

def _write_module_to_script(module_node: ast.Module, script_name: str) -> str:
    """Helper to write AST module to script file. Returns full script_path."""
    if not script_name.endswith(".py"): script_name += ".py"
    _ensure_base_dir_exists()
    script_path = os.path.join(BASE_PYTHON_OUTPUT_DIR, script_name)

    updated_script_content = to_source(module_node)
    with open(script_path, "w") as f: f.write(updated_script_content); f.flush()
    if not updated_script_content.endswith("\n"):
        with open(script_path, "a") as f: f.write("\n"); f.flush()
    return script_path


def add_function_to_script(script_name: str, function_name: str, parameters: list = None) -> str:
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error

    for node in module_node.body:
        if (isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef)) and node.name == function_name:
            return f"Error: Name '{function_name}' already exists in '{script_path}'." # Use full path in error

    param_nodes = [ast.arg(arg=p_name, annotation=None, type_comment=None) for p_name in (parameters or [])]
    args = ast.arguments(posonlyargs=[], args=param_nodes, vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
    new_function_node = ast.FunctionDef(name=function_name, args=args, body=[ast.Pass()], decorator_list=[], returns=None, type_comment=None)
    module_node.body.append(new_function_node)
    return _write_module_to_script(module_node, script_name) # script_name is just filename

def _parse_expression_to_ast_node(expression_str: str, allow_strings_without_quotes=False):
    try:
        parsed_expr_module = ast.parse(expression_str, mode='eval')
        return parsed_expr_module.body
    except SyntaxError as e_outer:
        if allow_strings_without_quotes:
            if expression_str.isidentifier() and not keyword.iskeyword(expression_str):
                 return ast.Name(id=expression_str, ctx=ast.Load())
            try: return ast.Constant(value=str(expression_str))
            except Exception as e_inner:
                raise ValueError(f"Could not parse '{expression_str}' as expr/var/str. Outer: {e_outer}, Inner: {e_inner}")
        raise ValueError(f"Could not parse expression: '{expression_str}'. Error: {e_outer}")

def _create_statement_node_from_desc(command_desc: dict):
    cmd_type = command_desc.get("type")
    expression_str = command_desc.get("expression")
    if cmd_type == "pass": return ast.Pass()
    if cmd_type == "assign":
        target_var_name = command_desc.get("target")
        if not target_var_name or not expression_str: raise ValueError("Missing target/expression for assign.")
        target_node = ast.Name(id=target_var_name, ctx=ast.Store())
        value_node = _parse_expression_to_ast_node(expression_str, allow_strings_without_quotes=True)
        return ast.Assign(targets=[target_node], value=value_node)
    if not expression_str and cmd_type in ["print", "return"]: raise ValueError(f"Expression missing for '{cmd_type}' command.")
    value_node = _parse_expression_to_ast_node(expression_str, allow_strings_without_quotes=(cmd_type=="print"))
    if cmd_type == "print": return ast.Expr(value=ast.Call(func=ast.Name(id='print', ctx=ast.Load()), args=[value_node], keywords=[]))
    elif cmd_type == "return": return ast.Return(value=value_node)
    else: raise ValueError(f"Unsupported body command type: {cmd_type}")

def add_statement_to_function_or_method(script_name: str, item_name: str, statement_type: str, item_type: str = "function", **kwargs) -> str:
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error

    target_body_owner_node = None
    if item_type == "function":
        func_name_to_find = item_name
        for node_in_body in module_node.body:
            if isinstance(node_in_body, ast.FunctionDef) and node_in_body.name == func_name_to_find:
                target_body_owner_node = node_in_body; break
        if not target_body_owner_node: return f"Error: Function '{func_name_to_find}' not found in '{script_path}'."
    elif item_type == "method":
        class_name, method_name = item_name.split('.') if '.' in item_name else (None, None)
        if not class_name or not method_name: return f"Error: Invalid method name '{item_name}'. Use 'ClassName.method_name'."
        class_node = None
        for node_in_body in module_node.body:
            if isinstance(node_in_body, ast.ClassDef) and node_in_body.name == class_name:
                class_node = node_in_body; break
        if not class_node: return f"Error: Class '{class_name}' not found in '{script_path}'."
        for method_node_in_class in class_node.body:
            if isinstance(method_node_in_class, ast.FunctionDef) and method_node_in_class.name == method_name: target_body_owner_node = method_node_in_class; break
        if not target_body_owner_node: return f"Error: Method '{method_name}' not found in class '{class_name}' in '{script_path}'."
    else: return f"Error: Invalid item_type '{item_type}'."

    try:
        new_statement_ast = None
        # ... (Dispatch logic for different statement_types as before, using _create_statement_node_from_desc for simple ones)
        if statement_type in ["print", "return", "pass", "assign"]:
             command_desc = {"type": statement_type};
             if "expression_str" in kwargs: command_desc["expression"] = kwargs["expression_str"]
             if "target_str" in kwargs: command_desc["target"] = kwargs["target_str"] # For assign
             new_statement_ast = _create_statement_node_from_desc(command_desc)
        elif statement_type == "conditional":
            if_condition_str = kwargs.get("if_condition_str"); if_body_command_dict = kwargs.get("if_body_command_dict"); else_body_command_dict = kwargs.get("else_body_command_dict")
            if not if_condition_str or not if_body_command_dict: raise ValueError("Missing details for if-statement.")
            test_node = _parse_expression_to_ast_node(if_condition_str); if_body_nodes = [_create_statement_node_from_desc(if_body_command_dict)]; orelse_nodes = []
            if else_body_command_dict and else_body_command_dict.get("type") != "unknown_statement": orelse_nodes = [_create_statement_node_from_desc(else_body_command_dict)]
            new_statement_ast = ast.If(test=test_node, body=if_body_nodes, orelse=orelse_nodes if orelse_nodes else None)
        elif statement_type == "for_loop":
            loop_var_str = kwargs.get("loop_var_str"); iterable_str = kwargs.get("iterable_str"); body_command_dict = kwargs.get("body_command_dict")
            if not loop_var_str or not iterable_str or not body_command_dict: raise ValueError("Missing details for for-loop.")
            target_node = ast.Name(id=loop_var_str, ctx=ast.Store()); iter_node = _parse_expression_to_ast_node(iterable_str); body_nodes = [_create_statement_node_from_desc(body_command_dict)]
            new_statement_ast = ast.For(target=target_node, iter=iter_node, body=body_nodes, orelse=None, type_comment=None)
        elif statement_type == "while_loop":
            condition_str = kwargs.get("condition_str"); body_command_dict = kwargs.get("body_command_dict")
            if not condition_str or not body_command_dict: raise ValueError("Missing details for while-loop.")
            test_node = _parse_expression_to_ast_node(condition_str); body_nodes = [_create_statement_node_from_desc(body_command_dict)]
            new_statement_ast = ast.While(test=test_node, body=body_nodes, orelse=None)
        elif statement_type == "file_operation":
            filename_expr_str = kwargs.get("filename_str"); file_mode_str = kwargs.get("file_mode_str"); file_var_name = kwargs.get("file_variable_name"); file_action_desc = kwargs.get("file_action_desc")
            if not all([filename_expr_str, file_mode_str, file_var_name, file_action_desc]): raise ValueError("Missing details for file op.")
            filename_node = _parse_expression_to_ast_node(filename_expr_str, allow_strings_without_quotes=False)
            mode_node = ast.Constant(value=file_mode_str)
            with_item = ast.withitem(context_expr=ast.Call(func=ast.Name(id='open', ctx=ast.Load()), args=[filename_node, mode_node], keywords=[]), optional_vars=ast.Name(id=file_var_name, ctx=ast.Store()))
            with_body = []; action_type = file_action_desc.get("type")
            if action_type == "read_assign":
                assign_target = ast.Name(id=file_action_desc["assign_to_var"], ctx=ast.Store()); read_call = ast.Call(func=ast.Attribute(value=ast.Name(id=file_var_name, ctx=ast.Load()), attr='read', ctx=ast.Load()), args=[], keywords=[]); assign_stmt = ast.Assign(targets=[assign_target], value=read_call); with_body.append(assign_stmt)
            elif action_type == "read_expr": read_call = ast.Call(func=ast.Attribute(value=ast.Name(id=file_var_name, ctx=ast.Load()), attr='read', ctx=ast.Load()), args=[], keywords=[]); with_body.append(ast.Expr(value=read_call))
            elif action_type == "write": value_to_write_node = _parse_expression_to_ast_node(file_action_desc["write_expression"], allow_strings_without_quotes=True); write_call = ast.Call(func=ast.Attribute(value=ast.Name(id=file_var_name, ctx=ast.Load()), attr='write', ctx=ast.Load()), args=[value_to_write_node], keywords=[]); with_body.append(ast.Expr(value=write_call))
            else: with_body.append(ast.Pass())
            new_statement_ast = ast.With(items=[with_item], body=with_body, type_comment=None)
        elif statement_type == "try_except":
            try_body_desc = kwargs["try_body_command_desc"]; exception_type_str = kwargs.get("exception_type_str"); exception_as_var = kwargs.get("exception_as_variable"); except_body_desc = kwargs["except_body_command_desc"]
            if not try_body_desc or not except_body_desc: raise ValueError("Missing body for try or except.")
            try_body_nodes = [_create_statement_node_from_desc(try_body_desc)]; except_body_nodes = [_create_statement_node_from_desc(except_body_desc)]; except_handler_type_node = None
            if exception_type_str:
                if exception_type_str.isidentifier() and not keyword.iskeyword(exception_type_str): except_handler_type_node = ast.Name(id=exception_type_str, ctx=ast.Load())
                else:
                    try: except_handler_type_node = _parse_expression_to_ast_node(exception_type_str)
                    except ValueError: raise ValueError(f"Invalid exception type: '{exception_type_str}'")
            except_handler = ast.ExceptHandler(type=except_handler_type_node, name=exception_as_var, body=except_body_nodes)
            new_statement_ast = ast.Try(body=try_body_nodes, handlers=[except_handler], orelse=[], finalbody=[])
        else: return f"Error: Unknown statement type '{statement_type}'."
    except ValueError as ve: return f"Error in statement: {ve}"
    except Exception as e: return f"Error creating statement node: {type(e).__name__} - {e}"

    if len(target_body_owner_node.body) == 1 and isinstance(target_body_owner_node.body[0], ast.Pass):
        target_body_owner_node.body = []
    target_body_owner_node.body.append(new_statement_ast)
    return _write_module_to_script(module_node, script_name)

def _does_import_exist(module_node_body_list, import_type, module_name_to_check, names_to_check=None):
    for node_in_list in module_node_body_list:
        if import_type == "direct_import":
            if isinstance(node_in_list, ast.Import):
                for alias in node_in_list.names:
                    if alias.name == module_name_to_check and alias.asname is None: return True
        elif import_type == "from_import":
            if isinstance(node_in_list, ast.ImportFrom) and node_in_list.module == module_name_to_check:
                if any(alias.name == '*' for alias in node_in_list.names): return True
                if names_to_check and all(name in {al.name for al in node_in_list.names} for name in names_to_check): return True
    return False

def add_import_to_script(script_name: str, import_details: dict) -> str:
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error
    import_type = import_details.get("import_type"); newly_created_node = None; modified_existing_node = False
    # ... (rest of import logic as before)
    if import_type == "direct_import":
        module_names_requested = import_details.get("modules", [])
        if not module_names_requested: return "Error: No modules specified for direct import."
        aliases_to_create = []
        for mod_name in module_names_requested:
            if not _does_import_exist(module_node.body, "direct_import", mod_name): aliases_to_create.append(ast.alias(name=mod_name, asname=None))
        if not aliases_to_create: return script_path # All exist, return path
        newly_created_node = ast.Import(names=aliases_to_create)
    elif import_type == "from_import":
        module_name = import_details.get("module"); names_requested = import_details.get("names", [])
        if not module_name or not names_requested: return "Error: Module or names missing."
        if _does_import_exist(module_node.body, "from_import", module_name, names_to_check=['*']): return script_path # Covers all
        existing_node_instance = None
        for node_in_script_body in module_node.body:
            if isinstance(node_in_script_body, ast.ImportFrom) and node_in_script_body.module == module_name: existing_node_instance = node_in_script_body; break
        if existing_node_instance:
            current_node_names = {alias.name for alias in existing_node_instance.names}
            names_to_actually_add = [name for name in names_requested if name not in current_node_names]
            if not names_to_actually_add: return script_path # All names already there
            for name_val in names_to_actually_add: existing_node_instance.names.append(ast.alias(name=name_val, asname=None))
            existing_node_instance.names.sort(key=lambda x: x.name); modified_existing_node = True
        else:
            aliases = [ast.alias(name=n, asname=None) for n in names_requested]
            newly_created_node = ast.ImportFrom(module=module_name, names=aliases, level=0)
    else: return "Error: Unknown import type."

    if newly_created_node:
        insert_pos = 0
        if module_node.body and isinstance(module_node.body[0], ast.Expr) and isinstance(module_node.body[0].value, ast.Constant): insert_pos = 1
        # Simplified duplicate check for this context; actual add_import_to_script has more robust checks
        module_node.body.insert(insert_pos, newly_created_node)

    if newly_created_node or modified_existing_node:
        return _write_module_to_script(module_node, script_name)
    return script_path # No changes made, but operation considered successful in terms of state

def add_class_to_script(script_name: str, class_name: str) -> str:
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error
    for node_in_module_body in module_node.body:
        if (isinstance(node_in_module_body, ast.ClassDef) or isinstance(node_in_module_body, ast.FunctionDef)) and \
           node_in_module_body.name == class_name:
            return f"Error: Name '{class_name}' already exists in '{script_path}'."
    new_class_node = ast.ClassDef(name=class_name, bases=[], keywords=[], body=[ast.Pass()], decorator_list=[])
    insert_pos = 0 # ... (insert logic as before)
    if module_node.body and isinstance(module_node.body[0], ast.Expr) and isinstance(module_node.body[0].value, ast.Constant): insert_pos = 1
    last_import_idx = -1;
    for idx, node_item in enumerate(module_node.body):
        if isinstance(node_item, (ast.Import, ast.ImportFrom)): last_import_idx = idx
    if last_import_idx != -1: insert_pos = last_import_idx + 1
    module_node.body.insert(insert_pos, new_class_node)
    return _write_module_to_script(module_node, script_name)

def add_method_to_class(script_name: str, class_name: str, method_name: str, parameters: list = None) -> str:
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error
    class_node = None # ... (find class_node as before)
    for node in module_node.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name: class_node = node; break
    if not class_node: return f"Error: Class '{class_name}' not found in '{script_path}'."
    for item in class_node.body: # ... (check existing method/attr name)
        if hasattr(item, 'name') and item.name == method_name: return f"Error: Method/attribute '{method_name}' already exists."
    processed_parameters = parameters[:] if parameters else []; # ... (ensure 'self')
    if not processed_parameters or processed_parameters[0].lower() != "self": processed_parameters.insert(0, "self")
    param_nodes = [ast.arg(arg=p_name, annotation=None, type_comment=None) for p_name in processed_parameters]
    args = ast.arguments(posonlyargs=[], args=param_nodes, vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
    new_method_node = ast.FunctionDef(name=method_name, args=args, body=[ast.Pass()], decorator_list=[], returns=None, type_comment=None)
    class_node.body.append(new_method_node)
    return _write_module_to_script(module_node, script_name)

def add_class_attribute_to_class(script_name: str, class_name: str, attribute_name: str, value_expression: str) -> str:
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error
    class_node = None # ... (find class_node and check existing attr/method as before)
    for node in module_node.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name: class_node = node; break
    if not class_node: return f"Error: Class '{class_name}' not found in '{script_path}'."
    for class_item_node in class_node.body: # ... (check existing)
        if isinstance(class_item_node, ast.Assign):
            for target in class_item_node.targets:
                if isinstance(target, ast.Name) and target.id == attribute_name: return f"Error: Attribute '{attribute_name}' already exists."
        elif hasattr(class_item_node, 'name') and class_item_node.name == attribute_name: return f"Error: Name '{attribute_name}' already exists as method."
    try: # ... (create assign_node as before)
        target_node = ast.Name(id=attribute_name, ctx=ast.Store())
        try: value_node = _parse_expression_to_ast_node(value_expression, allow_strings_without_quotes=False)
        except ValueError: value_node = _parse_expression_to_ast_node(value_expression, allow_strings_without_quotes=True)
    except ValueError as ve: return f"Error parsing value for attr '{attribute_name}': {ve}"
    assign_node = ast.Assign(targets=[target_node], value=value_node)
    # ... (insert logic as before)
    if not class_node.body or (len(class_node.body) == 1 and isinstance(class_node.body[0], ast.Pass)): class_node.body = [assign_node]
    else:
        insert_pos = 0
        if isinstance(class_node.body[0], ast.Expr) and isinstance(class_node.body[0].value, ast.Constant): insert_pos = 1
        if len(class_node.body) > insert_pos and isinstance(class_node.body[insert_pos], ast.Pass): class_node.body[insert_pos] = assign_node
        else: class_node.body.insert(insert_pos, assign_node)
    return _write_module_to_script(module_node, script_name)

def _ensure_init_method(class_node: ast.ClassDef, init_param_names: list = None) -> ast.FunctionDef:
    # ... (implementation as before)
    init_method_node = None
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == "__init__": init_method_node = node; break
    if not init_method_node:
        self_arg = ast.arg(arg="self", annotation=None, type_comment=None); param_nodes = [self_arg]
        if init_param_names:
            for p_name in init_param_names:
                if p_name != "self": param_nodes.append(ast.arg(arg=p_name, annotation=None, type_comment=None))
        args_ast = ast.arguments(posonlyargs=[], args=param_nodes, vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
        init_method_node = ast.FunctionDef(name="__init__", args=args_ast, body=[ast.Pass()], decorator_list=[], returns=None, type_comment=None)
        insert_pos = 0
        if class_node.body and isinstance(class_node.body[0], ast.Expr) and isinstance(class_node.body[0].value, ast.Constant): insert_pos = 1
        if len(class_node.body) == insert_pos: class_node.body.append(init_method_node)
        elif isinstance(class_node.body[insert_pos], ast.Pass): class_node.body[insert_pos] = init_method_node
        else: class_node.body.insert(insert_pos, init_method_node)
    else:
        if init_param_names:
            existing_params = {arg.arg for arg in init_method_node.args.args}
            for p_name in init_param_names:
                if p_name not in existing_params: init_method_node.args.args.append(ast.arg(arg=p_name, annotation=None, type_comment=None))
    return init_method_node

def add_instance_attribute_to_init(script_name: str, class_name: str, attribute_name: str, value_expression_str: str, init_param_suggestion: str = None) -> str:
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error
    # ... (rest of logic as before, use _write_module_to_script at the end)
    class_node = None
    for node in module_node.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name: class_node = node; break
    if not class_node: return f"Error: Class '{class_name}' not found in '{script_path}'."
    params_for_init = ["self"];
    if init_param_suggestion: params_for_init.append(init_param_suggestion)
    init_method_node = _ensure_init_method(class_node, params_for_init)
    for stmt_node in init_method_node.body: # ... (check existing self.attribute)
        if isinstance(stmt_node, ast.Assign):
            for target in stmt_node.targets:
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self' and target.attr == attribute_name:
                    return f"Error: Instance attribute 'self.{attribute_name}' already assigned in __init__."
    try: # ... (create assign_node for self.attribute)
        target_attr_node = ast.Attribute(value=ast.Name(id='self', ctx=ast.Load()), attr=attribute_name, ctx=ast.Store())
        value_node = _parse_expression_to_ast_node(value_expression_str, allow_strings_without_quotes=False)
    except ValueError as ve: return f"Error parsing value for instance attribute '{attribute_name}': {ve}"
    assign_node = ast.Assign(targets=[target_attr_node], value=value_node)
    if len(init_method_node.body) == 1 and isinstance(init_method_node.body[0], ast.Pass): init_method_node.body = [assign_node]
    else: init_method_node.body.append(assign_node)
    return _write_module_to_script(module_node, script_name)
