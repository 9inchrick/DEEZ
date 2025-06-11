import ast
import os

# (to_source and create_new_script remain the same)
def to_source(node):
    try:
        return ast.unparse(node)
    except AttributeError: # Basic fallback
        if isinstance(node, ast.Module): return "\n".join(to_source(n) for n in node.body)
        if isinstance(node, ast.FunctionDef):
            args_str = ", ".join(arg.arg for arg in node.args.args)
            body_parts = [to_source(n) for n in node.body]
            body_str = "\n".join(f"  {part}" for part in body_parts) if body_parts else "  pass"
            if "\n" in body_str: # Basic re-indent for multi-line bodies in fallback
                lines = body_str.splitlines()
                if not (len(lines) == 1 and lines[0].strip() == "pass"):
                    indented_lines = []
                    for i, line in enumerate(lines):
                        stripped_line = line.strip()
                        # Avoid double-indenting already indented lines from nested calls
                        if stripped_line.startswith("def ") or stripped_line.startswith("print(") or stripped_line.startswith("return "):
                             indented_lines.append(f"  {stripped_line}") # assume it's a flat structure for this simple fallback
                        elif i == 0 :
                            indented_lines.append(f"  {stripped_line}")
                        elif stripped_line:
                             indented_lines.append(f"    {stripped_line}") # Heuristic: further indent subsequent lines
                        else:
                            indented_lines.append("")
                    body_str = "\n".join(indented_lines)

            return f"def {node.name}({args_str}):\n{body_str if body_str.strip() else '  pass'}"
        if isinstance(node, ast.Pass): return "pass"
        if isinstance(node, ast.Expr): # Could be a docstring or a call like print()
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return f'"""{node.value.value}"""' # Docstring
            return to_source(node.value) # Other expressions like calls
        # Fallbacks for print and return (simplified)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print':
            arg_str = ", ".join([to_source(arg) for arg in node.args])
            return f"print({arg_str})"
        if isinstance(node, ast.Return):
            return f"return {to_source(node.value) if node.value else ''}"
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Constant): return repr(node.value) # handles strings, numbers
        if isinstance(node, ast.BinOp): # Very simplified
            op_map = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/', ast.Pow: '**',
                      ast.FloorDiv: '//', ast.Mod: '%', ast.LShift: '<<', ast.RShift: '>>',
                      ast.BitOr: '|', ast.BitXor: '^', ast.BitAnd: '&', ast.MatMult: '@'}
            left_source = to_source(node.left)
            right_source = to_source(node.right)
            return f"{left_source} {op_map.get(type(node.op), '?')} {right_source}"
        return "# AST unparsing issue for statement"

def create_new_script(script_name: str, initial_comment: str = None) -> str:
    if not script_name.endswith(".py"): script_name += ".py"
    output_dir = "generated_scripts"; os.makedirs(output_dir, exist_ok=True)
    script_path = os.path.join(output_dir, script_name)
    if os.path.exists(script_path): raise FileExistsError(f"Script '{script_path}' already exists.")
    module_body = []
    if initial_comment:
        # Ensure docstring is an Expr node with a Constant value
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

# (add_function_to_script remains largely the same, ensure it adds pass_stmt initially)
def add_function_to_script(script_name: str, function_name: str, parameters: list = None) -> str:
    if not script_name.endswith(".py"): script_name += ".py"
    script_path = os.path.join("generated_scripts", script_name)
    if not os.path.exists(script_path): return f"Error: Script '{script_path}' not found."
    with open(script_path, "r") as f: source_code = f.read()
    try: module_node = ast.parse(source_code, filename=script_path)
    except SyntaxError as e: return f"Error parsing script '{script_path}': {e}"
    for node in module_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return f"Error: Function '{function_name}' already exists in '{script_name}'."
    param_nodes = [ast.arg(arg=p_name, annotation=None, type_comment=None) for p_name in (parameters or [])]
    args = ast.arguments(posonlyargs=[], args=param_nodes, vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
    pass_stmt = ast.Pass() # Ensure new functions start with a pass
    body = [pass_stmt]
    new_function_node = ast.FunctionDef(name=function_name, args=args, body=body, decorator_list=[], returns=None, type_comment=None)
    module_node.body.append(new_function_node)
    updated_script_content = to_source(module_node)
    with open(script_path, "w") as f:
        f.write(updated_script_content)
        if not updated_script_content.endswith("\n"): f.write("\n")
    return "Success"

def _parse_expression_to_ast_node(expression_str: str):
    """Attempts to parse a string into an AST expression node."""
    try:
        # 'eval' mode for expressions. For full statements, 'exec' would be needed.
        # Wrap in parentheses to help parser with operator precedence if it's a complex expression
        # However, ast.parse(mode='eval') should handle this.
        parsed_expr_module = ast.parse(expression_str, mode='eval')
        return parsed_expr_module.body # This is the actual expression node
    except SyntaxError as e_outer:
        # If direct parsing fails, try common cases or raise error.
        # Check if it's a simple string literal that user forgot to quote for the expression
        if not ((expression_str.startswith("'") and expression_str.endswith("'")) or \
                (expression_str.startswith('"') and expression_str.endswith('"'))):
            try:
                # Try parsing as a name (variable)
                if expression_str.isidentifier():
                     # Test if parsing "variable_name" works
                    ast.parse(f"_{expression_str}_ = {expression_str}", mode="exec")
                    return ast.Name(id=expression_str, ctx=ast.Load())
            except SyntaxError:
                # If it's not an identifier and not parseable as direct expression,
                # it might be intended as a string literal.
                # This is a heuristic. For robust solution, NLU should be more specific or user clarifies.
                # For now, we'll try to wrap it as a string constant.
                try:
                    return ast.Constant(value=str(expression_str)) # Convert to string
                except Exception as e_inner: # Catch error from ast.Constant if any
                    raise ValueError(f"Could not parse expression '{expression_str}' as a direct expression, variable, or string literal. Original error: {e_outer}, Attempted as string: {e_inner}")
        raise ValueError(f"Could not parse expression: {expression_str}. Error: {e_outer}")


def add_statement_to_function(script_name: str, function_name: str, statement_type: str, expression_str: str) -> str:
    """
    Adds a statement (print or return) to a function's body.
    expression_str is the string representation of what to print or return.
    """
    if not script_name.endswith(".py"): script_name += ".py"
    script_path = os.path.join("generated_scripts", script_name)

    if not os.path.exists(script_path): return f"Error: Script '{script_path}' not found."

    with open(script_path, "r") as f: source_code = f.read()
    try: module_node = ast.parse(source_code, filename=script_path)
    except SyntaxError as e: return f"Error parsing script '{script_path}': {e}"

    func_node = None
    for node_idx, node in enumerate(module_node.body):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            func_node = module_node.body[node_idx] # Get the actual node reference
            break
    
    if not func_node: return f"Error: Function '{function_name}' not found in '{script_name}'."

    # Prepare the expression AST node
    try:
        value_node = _parse_expression_to_ast_node(expression_str)
    except ValueError as ve:
        return str(ve)
    except Exception as e: # Catch other parsing errors
        return f"Error interpreting expression '{expression_str}': {e}"


    # Create the statement AST node
    new_statement = None
    if statement_type == "print":
        new_statement = ast.Expr(value=ast.Call(func=ast.Name(id='print', ctx=ast.Load()), args=[value_node], keywords=[]))
    elif statement_type == "return":
        new_statement = ast.Return(value=value_node)
    else:
        return f"Error: Unknown statement type '{statement_type}'."

    # If the function body currently only contains 'pass', remove it.
    if len(func_node.body) == 1 and isinstance(func_node.body[0], ast.Pass):
        func_node.body = []
    
    func_node.body.append(new_statement)

    updated_script_content = to_source(module_node)
    with open(script_path, "w") as f: f.write(updated_script_content)
    if not updated_script_content.endswith("\n"): f.write("\n")
    
    return "Success"
