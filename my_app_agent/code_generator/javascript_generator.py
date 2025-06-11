# my_app_agent/code_generator/javascript_generator.py
import os

def create_new_js_script(script_name: str, initial_comment: str = None) -> str:
    """
    Creates a new JavaScript file with an optional initial comment.
    Returns the path to the created script.
    """
    if not script_name.endswith(".js"):
        script_name += ".js"

    # Create a 'js' subdirectory within 'generated_scripts' if it doesn't exist
    output_dir = os.path.join("generated_scripts", "js")
    os.makedirs(output_dir, exist_ok=True)

    script_path = os.path.join(output_dir, script_name)

    if os.path.exists(script_path):
        raise FileExistsError(f"JavaScript script '{script_path}' already exists.")

    script_content = ""
    if initial_comment:
        script_content += f"// {initial_comment}\n"

    # Add a placeholder message or a very simple default statement
    script_content += "// JavaScript file created by MyAppAgent\n"
    script_content += "console.log('Hello from MyAppAgent!');\n"


    with open(script_path, "w") as f:
        f.write(script_content)

    return script_path
