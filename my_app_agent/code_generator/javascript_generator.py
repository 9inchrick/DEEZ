# my_app_agent/code_generator/javascript_generator.py
import os

BASE_JS_OUTPUT_DIR = os.path.join(os.path.expanduser('~'), 'Documents', 'MyAppAgent', 'generated_scripts', 'javascript')

def create_new_js_script(script_name: str, initial_comment: str = None) -> str:
    """
    Creates a new JavaScript file with an optional initial comment.
    Returns the full path to the created script.
    Raises FileExistsError if the script already exists.
    """
    if not script_name.endswith(".js"):
        script_name += ".js"

    os.makedirs(BASE_JS_OUTPUT_DIR, exist_ok=True)
    script_path = os.path.join(BASE_JS_OUTPUT_DIR, script_name)

    if os.path.exists(script_path):
        raise FileExistsError(f"JavaScript script '{script_path}' already exists.")

    script_content = ""
    if initial_comment:
        script_content += f"// {initial_comment}\n"

    script_content += "// JavaScript file created by MyAppAgent\n"
    script_content += "console.log('Hello from MyAppAgent!');\n"

    with open(script_path, "w") as f:
        f.write(script_content)

    return script_path
