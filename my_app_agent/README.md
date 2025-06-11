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
    *   Create new Python script files (`.py`) in `~/Documents/MyAppAgent/generated_scripts/python/`.
    *   Add new, empty functions, methods (including `self`), class attributes, and instance attributes (in `__init__`) to Python scripts.
    *   Add simple `print`, `return`, `if/else`, `for` loops, `while` loops, `try-except` blocks, and basic file operations (`with open(...)`) to functions or methods.
    *   Add `import` and `from ... import ...` statements.
    *   Create new, empty classes.
    *   Prevent overwriting existing scripts and name clashes where applicable.
*   **JavaScript Code Generation (Experimental):**
    *   Create new JavaScript script files (`.js`) in `~/Documents/MyAppAgent/generated_scripts/javascript/`.
*   Display the generated/modified code to the user.
*   Basic Tkinter UI with a two-pane layout and Python syntax highlighting (if Pygments is installed).

## How to Run

1.  Ensure you have **Python 3.9 or newer** installed.
2.  (Optional, for syntax highlighting in UI) Install Pygments: `pip install Pygments`
3.  Navigate to the `my_app_agent` project root directory.
4.  Run the agent:
    *   For the **Command-Line Interface (CLI)**:
        ```bash
        python agent.py
        ```
    *   For the **Graphical User Interface (GUI)** (Recommended):
        ```bash
        python ui/main_ui.py
        ```
5.  Interact with the agent. Generated scripts are saved in `YourUserDocuments/MyAppAgent/generated_scripts/`.

## Project Structure

```
my_app_agent/
├── agent.py                    # Main application logic (AgentCore) and CLI loop
├── conversational_engine/      # NLU and NLG modules
│   ├── __init__.py
│   ├── nlu.py
│   └── nlg.py
├── code_generator/             # Code generation modules
│   ├── __init__.py
│   ├── python_generator.py
│   └── javascript_generator.py
├── ui/                         # Tkinter UI files
│   ├── __init__.py
│   ├── main_ui.py
│   └── myappagent.ico          # Placeholder application icon
├── generated_scripts/          # (This directory is created in ~/Documents/MyAppAgent/)
│   ├── python/
│   └── javascript/
└── README.md                   # This file
```

## Known Limitations & Future Work
*   **Language Support:** Python is primary. JavaScript support is very basic.
*   **NLU Simplicity:** Regex-based NLU has limitations.
*   **Code Complexity:** Generated code structures are still relatively simple.
*   **AST Unparsing:** Requires Python 3.9+.
*   **No Automated Tests.**
*   **State Management:** Basic.
*   **Error Handling:** Can be more robust.
*   **Packaging**: Instructions are experimental. Output path for `generated_scripts` is now user-specific, which is good, but packaging has other considerations.

## Packaging for Windows with PyInstaller (Experimental)

This section provides basic instructions on how to package MyAppAgent as a standalone Windows executable using PyInstaller.

**Prerequisites:**
1.  Ensure Python 3.9+ is installed.
2.  Install PyInstaller: `pip install pyinstaller`
3.  (Recommended for UI) Install Pygments: `pip install Pygments`

**Building the Executable:**
1.  Navigate to the `my_app_agent` project root directory (i.e., the directory containing `agent.py`, `ui/`, etc.).
2.  Run PyInstaller from this directory:
    ```bash
    pyinstaller --onefile --windowed --name MyAppAgent --icon=ui/myappagent.ico ui/main_ui.py
    ```
    *   `--onefile`: Bundles everything into a single executable.
    *   `--windowed`: Prevents a console window from opening when the GUI is run.
    *   `--name MyAppAgent`: Sets the name of the executable to `MyAppAgent.exe`.
    *   `--icon=ui/myappagent.ico`: Specifies the application icon.
    *   `ui/main_ui.py`: The entry point script for the UI application.

3.  The executable (`MyAppAgent.exe`) will be found in a `dist` folder created in the `my_app_agent` directory.

**Considerations for Packaged Application:**
*   **`generated_scripts` Directory:** The agent saves generated scripts to `YourUserDocuments/MyAppAgent/generated_scripts/`. This is generally a good default for packaged applications.
*   **Application Icon:** The command above includes a placeholder icon (`ui/myappagent.ico`). **Replace `my_app_agent/ui/myappagent.ico` with a proper `.ico` file for your application before building.**
*   **Module Detection (Pygments, etc.):** If PyInstaller has trouble finding modules like Pygments, you might need to add them as hidden imports (`--hidden-import pygments.lexers.python`) or adjust the `.spec` file that PyInstaller generates.
*   **Cross-Platform Building:** To build for different operating systems (e.g., macOS, Linux), you generally need to run PyInstaller on that specific OS.

This provides a starting point for creating a distributable version of MyAppAgent.
```
