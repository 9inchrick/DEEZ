import ast
import os

def to_source(node):
    """Converts an AST node to Python source code using ast.unparse.
    Requires Python 3.9+.
    """
    try:
        return ast.unparse(node)
    except AttributeError:
        # This error indicates ast.unparse is not available (e.g., Python < 3.9).
        print("ERROR: ast.unparse is not available. MyAppAgent requires Python 3.9+.")
        # Re-raising the AttributeError to make it clear what happened if not caught by a higher level.
        # Alternatively, could raise a custom error like RuntimeError or SystemExit.
        raise
    except Exception as e:
        # Catch any other unexpected errors during unparsing.
        print(f"ERROR: An unexpected error occurred during AST unparsing: {e}")
        raise # Re-raise the caught exception.

def create_new_script(script_name: str, initial_comment: str = None) -> str:
    if not script_name.endswith(".py"): script_name += ".py"
    output_dir = "generated_scripts"; os.makedirs(output_dir, exist_ok=True)
    script_path = os.path.join(output_dir, script_name)
    if os.path.exists(script_path): raise FileExistsError(f"Script '{script_path}' already exists.")
    module_body = []
    if initial_comment:
        module_body.append(ast.Expr(value=ast.Constant(value=initial_comment)))
    if not module_body:
        module_body.append(ast.Pass())
    module_node = ast.Module(body=module_body, type_ignores=[])
    script_content = to_source(module_node) # Relies on new to_source
    with open(script_path, "w") as f:
        f.write(script_content)
        if not script_content.endswith("\n") and script_content: f.write("\n")
        elif not script_content: f.write("\n")
    return script_path

def add_function_to_script(script_name: str, function_name: str, parameters: list = None) -> str:
    if not script_name.endswith(".py"): script_name += ".py"
    script_path = os.path.join("generated_scripts", script_name)
    if not os.path.exists(script_path): return f"Error: Script '{script_path}' not found."
    with open(script_path, "r") as f: source_code = f.read()
    try: module_node = ast.parse(source_code, filename=script_path)
    except SyntaxError as e: return f"Error parsing script '{script_path}': {e}"

    for node in module_node.body:
        if (isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef)) and node.name == function_name:
            return f"Error: Name '{function_name}' already exists as a function or class in '{script_name}'."

    param_nodes = [ast.arg(arg=p_name, annotation=None, type_comment=None) for p_name in (parameters or [])]
    args = ast.arguments(posonlyargs=[], args=param_nodes, vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
    pass_stmt = ast.Pass()
    body = [pass_stmt]
    new_function_node = ast.FunctionDef(name=function_name, args=args, body=body, decorator_list=[], returns=None, type_comment=None)
    module_node.body.append(new_function_node)
    updated_script_content = to_source(module_node) # Relies on new to_source
    with open(script_path, "w") as f:
        f.write(updated_script_content)
        if not updated_script_content.endswith("\n"): f.write("\n")
    return "Success"

def _parse_expression_to_ast_node(expression_str: str):
    try:
        parsed_expr_module = ast.parse(expression_str, mode='eval')
        return parsed_expr_module.body
    except SyntaxError as e_outer:
        if not ((expression_str.startswith("'") and expression_str.endswith("'")) or \
                (expression_str.startswith('"') and expression_str.endswith('"'))):
            try:
                if expression_str.isidentifier():
                    return ast.Name(id=expression_str, ctx=ast.Load())
            except SyntaxError:
                pass
            try:
                return ast.Constant(value=str(expression_str))
            except Exception as e_inner:
                raise ValueError(f"Could not parse expression '{expression_str}'. Original: {e_outer}, String attempt: {e_inner}")
        raise ValueError(f"Could not parse expression: {expression_str}. Error: {e_outer}")

def add_statement_to_function(script_name: str, function_name: str, statement_type: str, expression_str: str) -> str:
    if not script_name.endswith(".py"): script_name += ".py"
    script_path = os.path.join("generated_scripts", script_name)
    if not os.path.exists(script_path): return f"Error: Script '{script_path}' not found."
    with open(script_path, "r") as f: source_code = f.read()
    try: module_node = ast.parse(source_code, filename=script_path)
    except SyntaxError as e: return f"Error parsing script '{script_path}': {e}"

    func_node_found = None
    for node_in_body in module_node.body:
        if isinstance(node_in_body, ast.FunctionDef) and node_in_body.name == function_name:
            func_node_found = node_in_body
            break
    if not func_node_found: return f"Error: Function '{function_name}' not found in '{script_name}'."

    try: value_node = _parse_expression_to_ast_node(expression_str)
    except ValueError as ve: return str(ve)
    except Exception as e: return f"Error interpreting expression '{expression_str}': {e}"

    new_statement = None
    if statement_type == "print":
        new_statement = ast.Expr(value=ast.Call(func=ast.Name(id='print', ctx=ast.Load()), args=[value_node], keywords=[]))
    elif statement_type == "return":
        new_statement = ast.Return(value=value_node)
    else: return f"Error: Unknown statement type '{statement_type}'."

    if len(func_node_found.body) == 1 and isinstance(func_node_found.body[0], ast.Pass):
        func_node_found.body = []
    func_node_found.body.append(new_statement)

    updated_script_content = to_source(module_node) # Relies on new to_source
    with open(script_path, "w") as f: f.write(updated_script_content)
    if not updated_script_content.endswith("\n"): f.write("\n")
    return "Success"

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
    if not script_name.endswith(".py"): script_name += ".py"
    script_path = os.path.join("generated_scripts", script_name)
    if not os.path.exists(script_path): return f"Error: Script '{script_path}' not found."
    with open(script_path, "r") as f: source_code = f.read()
    try: module_node = ast.parse(source_code, filename=script_path)
    except SyntaxError as e: return f"Error parsing script '{script_path}': {e}"

    import_type = import_details.get("import_type")
    newly_created_node = None
    modified_existing_node = False

    if import_type == "direct_import":
        module_names_requested = import_details.get("modules", [])
        if not module_names_requested: return "Error: No modules specified for direct import."
        aliases_to_create = []
        for mod_name in module_names_requested:
            if not _does_import_exist(module_node.body, "direct_import", mod_name):
                aliases_to_create.append(ast.alias(name=mod_name, asname=None))
        if not aliases_to_create: return "Success: All specified direct imports already exist."
        newly_created_node = ast.Import(names=aliases_to_create)
    elif import_type == "from_import":
        module_name = import_details.get("module")
        names_requested = import_details.get("names", [])
        if not module_name or not names_requested: return "Error: Module or names missing for 'from ... import ...'."
        if _does_import_exist(module_node.body, "from_import", module_name, names_to_check=['*']):
             return f"Success: 'from {module_name} import *' already covers this."

        existing_node_instance = None
        for node_in_script_body in module_node.body:
            if isinstance(node_in_script_body, ast.ImportFrom) and node_in_script_body.module == module_name:
                existing_node_instance = node_in_script_body; break

        if existing_node_instance:
            current_node_names = {alias.name for alias in existing_node_instance.names}
            names_to_actually_add = [name for name in names_requested if name not in current_node_names]
            if not names_to_actually_add: return f"Success: All names from '{module_name}' already imported."
            for name_val in names_to_actually_add: existing_node_instance.names.append(ast.alias(name=name_val, asname=None))
            existing_node_instance.names.sort(key=lambda x: x.name)
            modified_existing_node = True
        else:
            aliases = [ast.alias(name=n, asname=None) for n in names_requested]
            newly_created_node = ast.ImportFrom(module=module_name, names=aliases, level=0)
    else: return "Error: Unknown import type."

    if newly_created_node:
        insert_pos = 0
        if module_node.body and isinstance(module_node.body[0], ast.Expr) and \
           isinstance(module_node.body[0].value, ast.Constant): insert_pos = 1

        is_duplicate_node = False
        for existing_node_check in module_node.body[0:insert_pos+len(module_node.body)]:
            if type(existing_node_check) == type(newly_created_node):
                if isinstance(existing_node_check, ast.Import) and isinstance(newly_created_node, ast.Import):
                    if sorted([al.name for al in existing_node_check.names]) == sorted([al.name for al in newly_created_node.names]):
                        is_duplicate_node = True; break
                elif isinstance(existing_node_check, ast.ImportFrom) and isinstance(newly_created_node, ast.ImportFrom):
                     if existing_node_check.module == newly_created_node.module and \
                        sorted([al.name for al in existing_node_check.names]) == sorted([al.name for al in newly_created_node.names]):
                        is_duplicate_node = True; break
        if not is_duplicate_node:
            module_node.body.insert(insert_pos, newly_created_node)
        elif not modified_existing_node:
             return "Success: Equivalent import statement already exists."

    if newly_created_node or modified_existing_node:
        updated_script_content = to_source(module_node) # Relies on new to_source
        with open(script_path, "w") as f: f.write(updated_script_content); f.flush()
        if not updated_script_content.endswith("\n"):
            with open(script_path, "a") as f: f.write("\n"); f.flush()
        return "Success"

    return "Success: No changes made to imports (already satisfied)."

def add_class_to_script(script_name: str, class_name: str) -> str:
    if not script_name.endswith(".py"): script_name += ".py"
    script_path = os.path.join("generated_scripts", script_name)
    if not os.path.exists(script_path): return f"Error: Script '{script_path}' not found."

    with open(script_path, "r") as f: source_code = f.read()
    try: module_node = ast.parse(source_code, filename=script_path)
    except SyntaxError as e: return f"Error parsing script '{script_path}': {e}"

    for node_in_module_body in module_node.body:
        if (isinstance(node_in_module_body, ast.ClassDef) or isinstance(node_in_module_body, ast.FunctionDef)) and \
           node_in_module_body.name == class_name:
            return f"Error: Name '{class_name}' already exists as a class or function in '{script_name}'."

    pass_stmt = ast.Pass()
    class_body = [pass_stmt]
    new_class_node = ast.ClassDef(name=class_name, bases=[], keywords=[], body=class_body, decorator_list=[])

    insert_pos = 0
    if module_node.body and isinstance(module_node.body[0], ast.Expr) and \
       isinstance(module_node.body[0].value, ast.Constant):
        insert_pos = 1

    last_import_idx = -1
    for idx, node_item in enumerate(module_node.body):
        if isinstance(node_item, (ast.Import, ast.ImportFrom)):
            last_import_idx = idx

    if last_import_idx != -1:
        insert_pos = last_import_idx + 1

    module_node.body.insert(insert_pos, new_class_node)

    updated_script_content = to_source(module_node) # Relies on new to_source
    with open(script_path, "w") as f:
        f.write(updated_script_content)
        if not updated_script_content.endswith("\n"): f.write("\n")

    return "Success"
