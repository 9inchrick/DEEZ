# my_app_agent/code_generator/__init__.py
from .python_generator import (
    create_new_script,
    add_function_to_script,
    add_statement_to_function,
    add_import_to_script,
    add_class_to_script
)
from .javascript_generator import create_new_js_script # Add this

__all__ = [
    "create_new_script",
    "add_function_to_script",
    "add_statement_to_function",
    "add_import_to_script",
    "add_class_to_script",
    "create_new_js_script" # Add this
]
