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
    os.makedirs(BASE_PYTHON_OUTPUT_DIR, exist_ok=True)

def create_new_script(script_name: str, initial_comment: str = None) -> str:
    if not script_name.endswith(".py"): script_name += ".py"
    _ensure_base_dir_exists()
    script_path = os.path.join(BASE_PYTHON_OUTPUT_DIR, script_name)
    if os.path.exists(script_path): raise FileExistsError(f"Python script '{script_path}' already exists.")
    module_body = [ast.Expr(value=ast.Constant(value=initial_comment))] if initial_comment else []
    if not module_body: module_body.append(ast.Pass())
    module_node = ast.Module(body=module_body, type_ignores=[])
    script_content = to_source(module_node)
    with open(script_path, "w") as f: f.write(script_content); f.write("\n" if not script_content.endswith("\n") else "")
    return script_path

def _read_and_parse_script(script_name: str) -> tuple[ast.Module | None, str | None, str | None]:
    if not script_name.endswith(".py"): script_name += ".py"
    _ensure_base_dir_exists()
    script_path = os.path.join(BASE_PYTHON_OUTPUT_DIR, script_name)
    if not os.path.exists(script_path): return None, None, f"Error: Script '{script_path}' not found."
    with open(script_path, "r") as f: source_code = f.read()
    try:
        module_node = ast.parse(source_code, filename=script_path)
        return module_node, script_path, None
    except SyntaxError as e:
        return None, script_path, f"Error parsing script '{script_path}': {e}"

def _write_module_to_script(module_node: ast.Module, script_name: str) -> str:
    if not script_name.endswith(".py"): script_name += ".py"
    _ensure_base_dir_exists()
    script_path = os.path.join(BASE_PYTHON_OUTPUT_DIR, script_name)
    updated_script_content = to_source(module_node)
    with open(script_path, "w") as f: f.write(updated_script_content); f.flush()
    if not updated_script_content.endswith("\n"):
        with open(script_path, "a") as f: f.write("\n"); f.flush()
    return script_path

def _get_target_function_or_method_node(module_node: ast.Module, item_name: str, item_type: str, class_name_for_method: str = None) -> ast.FunctionDef | None:
    """Helper to find a FunctionDef node for a global function or a method in a class."""
    if item_type == "function":
        return next((n for n in module_node.body if isinstance(n, ast.FunctionDef) and n.name == item_name), None)
    elif item_type == "method":
        if not class_name_for_method: return None # Class name is required for methods
        class_node = next((n for n in module_node.body if isinstance(n, ast.ClassDef) and n.name == class_name_for_method), None)
        if not class_node: return None
        return next((m for m in class_node.body if isinstance(m, ast.FunctionDef) and m.name == item_name), None)
    return None

def add_function_to_script(script_name: str, function_name: str, parameters: list = None) -> str:
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error
    for node in module_node.body:
        if (isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef)) and node.name == function_name:
            return f"Error: Name '{function_name}' already exists in '{script_path}'."
    param_nodes = [ast.arg(arg=p_name, annotation=None, type_comment=None) for p_name in (parameters or [])]
    args = ast.arguments(posonlyargs=[], args=param_nodes, vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
    new_function_node = ast.FunctionDef(name=function_name, args=args, body=[ast.Pass()], decorator_list=[], returns=None, type_comment=None)
    module_node.body.append(new_function_node)
    return _write_module_to_script(module_node, script_name)

def _parse_expression_to_ast_node(expression_str: str) -> ast.expr:
    if not isinstance(expression_str, str): raise ValueError(f"Expression must be a string, got {type(expression_str)}")
    expression_str = expression_str.strip()
    if not expression_str: raise ValueError("Expression cannot be empty.")
    try:
        parsed_module = ast.parse(expression_str, mode='eval')
        if isinstance(parsed_module, ast.Expression) and isinstance(parsed_module.body, ast.expr): return parsed_module.body
        else: raise ValueError(f"Unexpected AST structure from ast.parse(mode='eval') for: {expression_str}")
    except SyntaxError as e:
        if expression_str.isidentifier() and not keyword.iskeyword(expression_str):
            return ast.Name(id=expression_str, ctx=ast.Load())
        # Check for simple attribute access like 'module.name' or 'obj.attr'
        # This is a basic check and might need to be more robust for complex attributes.
        # For decorators like @app.route, this is crucial.
        potential_attr_match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)+)$", expression_str)
        if potential_attr_match:
            parts = expression_str.split('.')
            node = ast.Name(id=parts[0], ctx=ast.Load())
            for i in range(1, len(parts)):
                node = ast.Attribute(value=node, attr=parts[i], ctx=ast.Load())
            return node
        raise ValueError(f"Could not parse expression '{expression_str}': Invalid Python syntax. {e.msg}")
    except Exception as e: raise ValueError(f"Unexpected error parsing expression '{expression_str}': {type(e).__name__} - {e}")

def _create_statement_node(command_desc: dict): # ... (as before)
    cmd_type = command_desc.get("type"); expression_str = command_desc.get("expression")
    if cmd_type == "pass": return ast.Pass()
    if cmd_type == "assign":
        target_var_name = command_desc.get("target")
        if not target_var_name or not expression_str: raise ValueError("Missing target/expression for assign.")
        target_node = ast.Name(id=target_var_name, ctx=ast.Store()); value_node = _parse_expression_to_ast_node(expression_str)
        return ast.Assign(targets=[target_node], value=value_node)
    if not expression_str and cmd_type in ["print", "return"]: raise ValueError(f"Expression missing for '{cmd_type}' command.")
    value_node = _parse_expression_to_ast_node(expression_str)
    if cmd_type == "print": return ast.Expr(value=ast.Call(func=ast.Name(id='print', ctx=ast.Load()), args=[value_node], keywords=[]))
    elif cmd_type == "return": return ast.Return(value=value_node)
    if cmd_type == "unknown_statement": raise ValueError(f"Unknown statement: {command_desc.get('raw_command')}")
    raise ValueError(f"Unsupported command type for node creation: {cmd_type}")

def _build_body_nodes(command_descs: list | None) -> list: # ... (as before)
    body_nodes = [];
    if command_descs:
        for cmd_desc in command_descs: body_nodes.append(_create_statement_node(cmd_desc))
    meaningful_nodes = [node for node in body_nodes if not isinstance(node, ast.Pass)]
    if meaningful_nodes: return meaningful_nodes
    elif body_nodes: return [ast.Pass()]
    return []

def add_statement_to_function_or_method(script_name: str, item_name: str, statement_type: str, item_type: str = "function", **kwargs) -> str: # ... (as before)
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error
    target_body_owner_node = _get_target_function_or_method_node(module_node, item_name, item_type, kwargs.get("class_name_for_method")) # Use helper
    if not target_body_owner_node: return f"Error: {item_type.capitalize()} '{item_name}' not found in '{script_path}'."
    try: # ... (dispatch logic as before, including try_except with else/finally)
        new_statement_ast = None
        if statement_type in ["print", "return", "pass", "assign"]: command_desc = {"type": statement_type}; # ...
        elif statement_type == "conditional": # ...
            if_condition_str = kwargs.get("if_condition_str"); if_body_descs = kwargs.get("if_body_command_descs"); elif_clauses_descs = kwargs.get("elif_clauses_descs"); else_body_descs = kwargs.get("else_body_command_descs")
            if not if_condition_str or not if_body_descs: raise ValueError("Missing condition or body for if-statement.")
            if_condition_node = _parse_expression_to_ast_node(if_condition_str); current_if_body_nodes = _build_body_nodes(if_body_descs); current_orelse_nodes = []
            if else_body_descs: current_orelse_nodes = _build_body_nodes(else_body_descs)
            if elif_clauses_descs:
                for elif_clause in reversed(elif_clauses_descs):
                    elif_condition_node = _parse_expression_to_ast_node(elif_clause["condition"]); elif_body_nodes = _build_body_nodes(elif_clause["body_command_descs"])
                    new_if_for_elif = ast.If(test=elif_condition_node, body=elif_body_nodes, orelse=current_orelse_nodes)
                    current_orelse_nodes = [new_if_for_elif]
            new_statement_ast = ast.If(test=if_condition_node, body=current_if_body_nodes, orelse=current_orelse_nodes)
        elif statement_type == "for_loop": # ...
            loop_var_str = kwargs.get("loop_var_str"); iterable_str = kwargs.get("iterable_str"); body_descs = kwargs.get("body_command_descs")
            if not loop_var_str or not iterable_str or not body_descs: raise ValueError("Missing details for for-loop.")
            target_node = ast.Name(id=loop_var_str, ctx=ast.Store()); iter_node = _parse_expression_to_ast_node(iterable_str); body_nodes = _build_body_nodes(body_descs)
            new_statement_ast = ast.For(target=target_node, iter=iter_node, body=body_nodes, orelse=[], type_comment=None)
        elif statement_type == "while_loop": # ...
            condition_str = kwargs.get("condition_str"); body_descs = kwargs.get("body_command_descs")
            if not condition_str or not body_descs: raise ValueError("Missing details for while-loop.")
            test_node = _parse_expression_to_ast_node(condition_str); body_nodes = _build_body_nodes(body_descs)
            new_statement_ast = ast.While(test=test_node, body=body_nodes, orelse=[])
        elif statement_type == "file_operation":  # ...
            filename_expr_str = kwargs.get("filename_str"); file_mode_str = kwargs.get("file_mode_str"); file_var_name = kwargs.get("file_variable_name"); file_action_desc = kwargs.get("file_action_desc")
            if not all([filename_expr_str, file_mode_str, file_var_name, file_action_desc]): raise ValueError("Missing details for file op.")
            filename_node = _parse_expression_to_ast_node(filename_expr_str); mode_node = ast.Constant(value=file_mode_str)
            with_item = ast.withitem(context_expr=ast.Call(func=ast.Name(id='open', ctx=ast.Load()), args=[filename_node, mode_node], keywords=[]), optional_vars=ast.Name(id=file_var_name, ctx=ast.Store()))
            with_body_nodes = [_create_statement_node(file_action_desc)]
            new_statement_ast = ast.With(items=[with_item], body=with_body_nodes, type_comment=None)
        elif statement_type == "try_except": # ... (as before with else/finally)
            try_body_descs = kwargs.get("try_body_command_descs"); exception_type_str = kwargs.get("exception_type_str"); exception_as_var = kwargs.get("exception_as_variable"); except_body_descs = kwargs.get("except_body_command_descs")
            else_body_descs = kwargs.get("else_body_command_descs"); finally_body_descs = kwargs.get("finally_body_command_descs")
            if not try_body_descs or not except_body_descs: raise ValueError("Missing body for try or except.")
            try_body_nodes = _build_body_nodes(try_body_descs); except_body_nodes = _build_body_nodes(except_body_descs); except_handler_type_node = None
            if exception_type_str:
                if exception_type_str.isidentifier() and not keyword.iskeyword(exception_type_str): except_handler_type_node = ast.Name(id=exception_type_str, ctx=ast.Load())
                else:
                    try: except_handler_type_node = _parse_expression_to_ast_node(exception_type_str)
                    except ValueError: raise ValueError(f"Invalid exception type: '{exception_type_str}'")
            except_handler = ast.ExceptHandler(type=except_handler_type_node, name=exception_as_var, body=except_body_nodes)
            orelse_nodes = _build_body_nodes(else_body_descs); finalbody_nodes = _build_body_nodes(finally_body_descs)
            new_statement_ast = ast.Try(body=try_body_nodes, handlers=[except_handler], orelse=orelse_nodes, finalbody=finalbody_nodes)
        else: return f"Error: Unknown statement type '{statement_type}'."
    except ValueError as ve: return f"Error in statement: {ve}"
    except Exception as e: return f"Error creating statement node: {type(e).__name__} - {e}"
    if len(target_body_owner_node.body) == 1 and isinstance(target_body_owner_node.body[0], ast.Pass): target_body_owner_node.body = []
    target_body_owner_node.body.append(new_statement_ast)
    return _write_module_to_script(module_node, script_name)

def add_import_to_script(script_name: str, import_details: dict) -> str: # ... (as before)
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error
    # ... (rest of logic)
    import_type = import_details.get("import_type"); newly_created_node = None; modified_existing_node = False
    if import_type == "direct_import": # ... (as before)
        module_names_requested = import_details.get("modules", []); aliases_to_create = []
        if not module_names_requested: return "Error: No modules specified."
        for mod_name in module_names_requested:
            if not _does_import_exist(module_node.body, "direct_import", mod_name): aliases_to_create.append(ast.alias(name=mod_name, asname=None))
        if not aliases_to_create: return script_path
        newly_created_node = ast.Import(names=aliases_to_create)
    elif import_type == "from_import": # ... (as before)
        module_name = import_details.get("module"); names_requested = import_details.get("names", [])
        if not module_name or not names_requested: return "Error: Module or names missing."
        if _does_import_exist(module_node.body, "from_import", module_name, names_to_check=['*']): return script_path
        existing_node_instance = next((n for n in module_node.body if isinstance(n, ast.ImportFrom) and n.module == module_name), None)
        if existing_node_instance:
            current_node_names = {alias.name for alias in existing_node_instance.names}
            names_to_actually_add = [name for name in names_requested if name not in current_node_names]
            if not names_to_actually_add: return script_path
            for name_val in names_to_actually_add: existing_node_instance.names.append(ast.alias(name=name_val, asname=None))
            existing_node_instance.names.sort(key=lambda x: x.name); modified_existing_node = True
        else: newly_created_node = ast.ImportFrom(module=module_name, names=[ast.alias(name=n, asname=None) for n in names_requested], level=0)
    else: return "Error: Unknown import type."
    if newly_created_node: insert_pos = 1 if module_node.body and isinstance(module_node.body[0], ast.Expr) else 0; module_node.body.insert(insert_pos, newly_created_node)
    if newly_created_node or modified_existing_node: return _write_module_to_script(module_node, script_name)
    return script_path

def add_class_to_script(script_name: str, class_name: str) -> str: # ... (as before)
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error
    if any((isinstance(n, ast.ClassDef) or isinstance(n, ast.FunctionDef)) and n.name == class_name for n in module_node.body): return f"Error: Name '{class_name}' already exists in '{script_path}'."
    new_class_node = ast.ClassDef(name=class_name, bases=[], keywords=[], body=[ast.Pass()], decorator_list=[])
    insert_pos = next((i+1 for i, stmt in enumerate(module_node.body) if isinstance(stmt, (ast.Import, ast.ImportFrom))), 0)
    if module_node.body and isinstance(module_node.body[0], ast.Expr) and insert_pos == 0 : insert_pos = 1 # After docstring
    module_node.body.insert(insert_pos, new_class_node)
    return _write_module_to_script(module_node, script_name)

def add_method_to_class(script_name: str, class_name: str, method_name: str, parameters: list = None, body_command_descs: list = None) -> str: # ... (as before)
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error
    class_node = next((n for n in module_node.body if isinstance(n, ast.ClassDef) and n.name == class_name), None)
    if not class_node: return f"Error: Class '{class_name}' not found in '{script_path}'."
    if any(hasattr(item, 'name') and item.name == method_name for item in class_node.body): return f"Error: Method/attribute '{method_name}' already exists."
    processed_parameters = parameters[:] if parameters else []; # ... (ensure 'self')
    if not processed_parameters or processed_parameters[0].lower() != "self": processed_parameters.insert(0, "self")
    param_nodes = [ast.arg(arg=p_name, annotation=None, type_comment=None) for p_name in processed_parameters]
    args = ast.arguments(posonlyargs=[], args=param_nodes, vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
    try: method_body_nodes = _build_body_nodes(body_command_descs if body_command_descs else [{"type":"pass"}])
    except ValueError as ve: return f"Error creating method body: {ve}"
    new_method_node = ast.FunctionDef(name=method_name, args=args, body=method_body_nodes, decorator_list=[], returns=None, type_comment=None)
    class_node.body.append(new_method_node)
    return _write_module_to_script(module_node, script_name)

def add_class_attribute_to_class(script_name: str, class_name: str, attribute_name: str, value_expression: str) -> str: # ... (as before)
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error
    class_node = next((n for n in module_node.body if isinstance(n, ast.ClassDef) and n.name == class_name), None)
    if not class_node: return f"Error: Class '{class_name}' not found in '{script_path}'."
    # ... (check existing attr/method)
    try: target_node = ast.Name(id=attribute_name, ctx=ast.Store()); value_node = _parse_expression_to_ast_node(value_expression)
    except ValueError as ve: return f"Error parsing value for attr '{attribute_name}': {ve}"
    assign_node = ast.Assign(targets=[target_node], value=value_node)
    # ... (insert logic as before)
    if not class_node.body or (len(class_node.body) == 1 and isinstance(class_node.body[0], ast.Pass)): class_node.body = [assign_node]
    else:
        insert_pos = 1 if class_node.body and isinstance(class_node.body[0], ast.Expr) else 0
        if len(class_node.body) > insert_pos and isinstance(class_node.body[insert_pos], ast.Pass): class_node.body[insert_pos] = assign_node
        else: class_node.body.insert(insert_pos, assign_node)
    return _write_module_to_script(module_node, script_name)

def _ensure_init_method(class_node: ast.ClassDef, init_param_names: list = None) -> ast.FunctionDef: # ... (as before)
    init_method_node = next((n for n in class_node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
    if not init_method_node:
        self_arg = ast.arg(arg="self", annotation=None, type_comment=None); param_nodes = [self_arg]
        if init_param_names:
            for p_name in init_param_names:
                if p_name != "self": param_nodes.append(ast.arg(arg=p_name, annotation=None, type_comment=None))
        args_ast = ast.arguments(posonlyargs=[], args=param_nodes, vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
        init_method_node = ast.FunctionDef(name="__init__", args=args_ast, body=[ast.Pass()], decorator_list=[], returns=None, type_comment=None)
        insert_pos = 1 if class_node.body and isinstance(class_node.body[0], ast.Expr) else 0
        if len(class_node.body) == insert_pos: class_node.body.append(init_method_node)
        elif isinstance(class_node.body[insert_pos], ast.Pass): class_node.body[insert_pos] = init_method_node
        else: class_node.body.insert(insert_pos, init_method_node)
    else:
        if init_param_names:
            existing_params = {arg.arg for arg in init_method_node.args.args}
            for p_name in init_param_names:
                if p_name not in existing_params: init_method_node.args.args.append(ast.arg(arg=p_name, annotation=None, type_comment=None))
    return init_method_node

def add_instance_attribute_to_init(script_name: str, class_name: str, attribute_name: str, value_expression_str: str, init_param_suggestion: str = None) -> str: # ... (as before)
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error
    class_node = next((n for n in module_node.body if isinstance(n, ast.ClassDef) and n.name == class_name), None)
    if not class_node: return f"Error: Class '{class_name}' not found in '{script_path}'."
    params_for_init = ["self"];
    if init_param_suggestion: params_for_init.append(init_param_suggestion)
    init_method_node = _ensure_init_method(class_node, params_for_init)
    # ... (check existing self.attribute)
    for stmt_node in init_method_node.body:
        if isinstance(stmt_node, ast.Assign):
            for target in stmt_node.targets:
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self' and target.attr == attribute_name:
                    return f"Error: Instance attribute 'self.{attribute_name}' already assigned in __init__."
    try:
        target_attr_node = ast.Attribute(value=ast.Name(id='self', ctx=ast.Load()), attr=attribute_name, ctx=ast.Store())
        value_node = _parse_expression_to_ast_node(value_expression_str)
    except ValueError as ve: return f"Error parsing value for instance attribute '{attribute_name}': {ve}"
    assign_node = ast.Assign(targets=[target_attr_node], value=value_node)
    if len(init_method_node.body) == 1 and isinstance(init_method_node.body[0], ast.Pass): init_method_node.body = [assign_node]
    else: init_method_node.body.append(assign_node)
    return _write_module_to_script(module_node, script_name)

def add_decorator_to_function_or_method(script_name: str, item_name: str, item_type: str, decorator_expression_str: str, class_name_for_method: str = None) -> str:
    """Adds a decorator to a function or method. Returns full script_path or error string."""
    module_node, script_path, error = _read_and_parse_script(script_name)
    if error: return error

    target_func_node = _get_target_function_or_method_node(module_node, item_name, item_type, class_name_for_method)
    if not target_func_node:
        if item_type == "method": return f"Error: Method '{item_name}' in class '{class_name_for_method}' not found in '{script_path}'."
        return f"Error: Function '{item_name}' not found in '{script_path}'."
    if not isinstance(target_func_node, ast.FunctionDef): # Should be caught by _get_target_...
        return f"Error: Target '{item_name}' is not a function or method."

    if not decorator_expression_str: return "Error: Decorator expression not provided."
    try:
        decorator_node = _parse_expression_to_ast_node(decorator_expression_str)
    except ValueError as ve: return f"Error parsing decorator expression '@{decorator_expression_str}': {ve}"

    new_decorator_str = to_source(decorator_node)
    for existing_decorator_node in target_func_node.decorator_list:
        if to_source(existing_decorator_node) == new_decorator_str:
            return script_path # Decorator already exists, consider it a success, return path

    target_func_node.decorator_list.insert(0, decorator_node)
    return _write_module_to_script(module_node, script_name)
