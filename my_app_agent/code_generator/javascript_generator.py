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

    with open(script_path, "w", encoding='utf-8') as f: # Added encoding
        f.write(script_content)

    return script_path

def delete_script(script_filename: str) -> str:
    """Deletes a JavaScript script. Returns a success or error message string."""
    if not script_filename.endswith(".js"):
        return f"Error: Invalid filename, expected a .js extension: {script_filename}"

    os.makedirs(BASE_JS_OUTPUT_DIR, exist_ok=True) # Ensure base dir logic is consistent
    script_path = os.path.join(BASE_JS_OUTPUT_DIR, script_filename)

    try:
        if os.path.exists(script_path):
            os.remove(script_path)
            return f"Success: Script '{script_filename}' deleted."
        else:
            return f"Error: Script '{script_filename}' not found at '{script_path}'."
    except PermissionError:
        return f"Error: Permission denied. Could not delete script '{script_filename}' at '{script_path}'."
    except OSError as e:
        return f"Error: Could not delete script '{script_filename}' at '{script_path}': {e.strerror}"
    except Exception as e:
        return f"Error: An unexpected error occurred while deleting script '{script_filename}': {str(e)}"
