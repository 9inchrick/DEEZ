# MyAppAgent - An App Building Agent

MyAppAgent is a conversational agent designed to assist in building applications.
This is an early-stage project focusing on understanding user requests in natural
language and generating code.

## Requirements

*   **Python 3.9 or newer is required.** This is due to the reliance on `ast.unparse` for generating Python code from Abstract Syntax Trees (ASTs).

## Current Capabilities

As of the current version, MyAppAgent can:

*   Engage in a basic text-based conversation to understand commands.
*   Manage a context of the "active language" (Python and experimental JavaScript).
*   Manage a context of the "current script" being worked on.
*   **Python Code Generation (requires Python 3.9+):**
    *   Create new Python script files (`.py`) in a `generated_scripts/` directory.
    *   Add new, empty functions (`def function_name(): pass`) to existing Python scripts, including parameters in the function signature (e.g., `def my_func(a, b): pass`).
    *   Add simple `print()` or `return` statements to the body of existing functions.
    *   Add `import` and `from ... import ...` statements to Python scripts, with basic duplicate avoidance.
    *   Create new, empty classes (`class ClassName: pass`) in Python scripts.
    *   Prevent overwriting existing scripts when creating new ones.
    *   Prevent adding functions or classes if a function or class with the same name already exists in the script.
*   **JavaScript Code Generation (Experimental):**
    *   Create new JavaScript script files (`.js`) in a `generated_scripts/js/` directory with a basic comment and `console.log` statement.
*   Display the generated/modified code to the user after an action.

## How to Run

1.  Ensure you have **Python 3.9 or newer** installed.
2.  Navigate to the directory containing `agent.py` (i.e., the `my_app_agent` directory if you are one level above it).
3.  Run the agent from within the `my_app_agent` directory:
    ```bash
    python agent.py
    ```
    Or, if you are in the parent directory of `my_app_agent`:
    ```bash
    python my_app_agent/agent.py
    ```
4.  Interact with the agent by typing commands at the prompt. Examples:
    *   `use python`
    *   `create a script named my_new_app.py`
    *   `add function setup_database(config_file, retries) to my_new_app.py`
    *   `in function setup_database in script my_new_app.py print 'Initializing...'`
    *   `from utils import helper_function into my_new_app.py`
    *   `create class MyUtilityClass in my_new_app.py`
    *   `use javascript`
    *   `create script my_web_script.js`
    *   `exit` (to close the agent)

## Project Structure

```
my_app_agent/
├── agent.py                    # Main application logic and user interaction loop
├── conversational_engine/      # Modules for understanding and responding to user
│   ├── __init__.py
│   ├── nlu.py                  # Natural Language Understanding
│   └── nlg.py                  # Natural Language Generation
├── code_generator/             # Modules for generating code
│   ├── __init__.py
│   ├── python_generator.py     # Python code generation logic (using AST)
│   └── javascript_generator.py # JavaScript code generation logic (basic)
├── generated_scripts/          # Directory where generated scripts are saved
│   └── js/                     # Subdirectory for JavaScript files
└── tests/                      # Placeholder for future automated tests
    └── __init__.py
└── README.md                   # This file
```

## Known Limitations & Future Work

*   **Language Support:** Primary support for Python (via AST manipulation). JavaScript support is experimental and currently limited to creating basic script files. Other languages are not yet supported.
*   **NLU Simplicity:** The Natural Language Understanding is based on simple regex matching and has limited scope. More advanced NLU (e.g., using machine learning models) would be needed for broader understanding.
*   **Code Complexity (Python):** Can only generate relatively simple structures (empty scripts, functions with empty bodies or simple print/return, empty classes, basic imports). Cannot yet:
    *   Implement complex function bodies or logic.
    *   Add methods or attributes to classes.
    *   Handle type hints, decorators (beyond basic parsing), or more complex argument types.
    *   Manage dependencies between generated code components effectively.
*   **Code Complexity (JavaScript):** Limited to creating a file with a comment and a `console.log`. No AST manipulation or deeper code generation for JS yet.
*   **AST Unparsing:** Uses `ast.unparse` for Python and thus requires Python 3.9+. This provides reliable code generation from the AST for Python.
*   **No Automated Tests:** Testing is currently manual. Adding a test suite is crucial for future development.
*   **State Management:** Basic state management for current language and script. More complex project-level state (e.g., managing multiple files, symbols across files) is future work.
*   **Error Handling:** Error handling for code generation and NLU parsing is basic. More robust error recovery and user feedback mechanisms are needed.
*   **Contextual Understanding:** The agent's understanding of context is limited. It doesn't "remember" details beyond the current script and language or previously defined symbols in a deep way.

This project serves as a foundational exploration into building code-generating conversational agents.
```
