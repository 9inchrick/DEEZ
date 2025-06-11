# MyAppAgent - An App Building Agent

MyAppAgent is a conversational agent designed to assist in building applications. 
This is an early-stage project focusing on understanding user requests in natural
language and generating code.

## Current Capabilities

As of the current version, MyAppAgent can:

*   Engage in a basic text-based conversation to understand commands.
*   Manage a context of the "active language" (currently only supporting Python for code generation).
*   Manage a context of the "current script" being worked on.
*   **Python Code Generation:**
    *   Create new Python script files (`.py`) in a `generated_scripts/` directory.
    *   Add new, empty functions (`def function_name(): pass`) to existing Python scripts.
    *   Prevent overwriting existing scripts and adding functions with duplicate names within the same script.
*   Display the generated/modified code to the user after an action.

## How to Run

1.  Ensure you have Python installed (Python 3.9+ recommended for full `ast.unparse` features; otherwise, the `astor` library might be needed for robust AST to source conversion, though it's not an explicit dependency in this version).
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
    *   `create a script named my_new_app.py`
    *   `add function setup_database`
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
│   └── python_generator.py     # Python code generation logic (using AST)
├── generated_scripts/          # Directory where generated scripts are saved (created automatically)
└── tests/                      # Placeholder for future automated tests
    └── __init__.py
└── README.md                   # This file
```

## Known Limitations & Future Work

*   **Language Support:** Currently only generates Python code. The architecture is designed to be extensible for other languages.
*   **NLU Simplicity:** The Natural Language Understanding is based on simple regex matching and has limited scope.
*   **Code Complexity:** Can only generate very simple structures (empty scripts, empty functions). Cannot yet add parameters to functions, implement function bodies, create classes, handle imports, etc.
*   **AST Unparsing:** Relies on `ast.unparse` (Python 3.9+) or a very basic fallback for converting AST to source. For robust support on older Python versions or for more complex ASTs, the `astor` library would be a good addition.
*   **No Automated Tests:** Testing is currently manual.
*   **State Management:** Basic state management for current language and script. More complex project-level state is future work.

This project serves as a foundational exploration into building code-generating conversational agents.
