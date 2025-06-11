# MyAppAgent - An App Building Agent

MyAppAgent is a conversational agent designed to assist in building applications. 
This is an early-stage project focusing on understanding user requests in natural
language and generating code, with a PySide6 graphical user interface.

## Requirements

*   **Python 3.9 or newer is required.** (Due to `ast.unparse`).
*   **PySide6:** For the graphical user interface. Install using: `pip install PySide6`
*   **(Optional) Pygments:** For Python syntax highlighting in the UI's code view. Install using: `pip install Pygments`

## Current Capabilities

As of the current version, MyAppAgent can:

*   Engage in a basic text-based conversation to understand commands.
*   Manage a context of the "active language" (Python and experimental JavaScript).
*   Manage a context of the "current script" being worked on.
*   **Python Code Generation (requires Python 3.9+):**
    *   Create new Python script files (`.py`) in `~/Documents/MyAppAgent/generated_scripts/python/`.
    *   Add new, empty functions, methods (including `self`), class attributes, and instance attributes (in `__init__`) to Python scripts.
    *   Add simple `print`, `return`, `if/elif/else`, `for` loops, `while` loops, `try-except-else-finally` blocks, and basic file operations (`with open(...)`) to functions or methods. Multi-statement bodies (delimited by " then ") are supported for these structures.
    *   Add decorators to functions and methods.
    *   Add `import` and `from ... import ...` statements.
    *   Create new, empty classes.
    *   Prevent overwriting existing scripts and name clashes where applicable.
*   **JavaScript Code Generation (Experimental):**
    *   Create new JavaScript script files (`.js`) in `~/Documents/MyAppAgent/generated_scripts/javascript/`.
*   Display the generated/modified code to the user.
*   **PySide6 Graphical User Interface:**
    *   A three-pane layout: File Navigator, Code View, and Log/Console.
    *   File navigator to browse and open generated scripts.
    *   Python syntax highlighting in the Code View (uses `QSyntaxHighlighter`, no external Pygments dependency at runtime for this specific feature, but Pygments was used as a reference for token styles).
    *   Dark theme implemented using QSS.

## How to Run

1.  Ensure you have **Python 3.9 or newer** installed.
2.  Install PySide6: `pip install PySide6`
3.  (Optional, if you want to explore Pygments or if it becomes a direct dependency later) Install Pygments: `pip install Pygments`
4.  Navigate to the `my_app_agent` project root directory.
5.  **To run the GUI application (recommended):**
    ```bash
    python ui/main_ui_pyside.py
    ```
6.  **To run the command-line interface (for testing core logic):**
    ```bash
    python agent.py
    ```
7.  Generated scripts are saved by default in your `Documents/MyAppAgent/generated_scripts/` directory (under `python` or `javascript` subfolders).

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
├── ui/                         # User Interface files
│   ├── __init__.py
│   ├── main_ui_pyside.py       # Main PySide6 GUI application
│   └── myappagent.ico          # Placeholder application icon 
#   └── main_ui.py              # (Legacy Tkinter UI, if kept) 
├── generated_scripts/          # (This directory is created in ~/Documents/MyAppAgent/)
│   ├── python/
│   └── javascript/
└── README.md                   # This file
```

## Known Limitations & Future Work
*   **Language Support:** Python is primary. JavaScript support is very basic.
*   **NLU Simplicity:** Regex-based NLU has limitations.
*   **Code Complexity:** Generated code structures (e.g., bodies of loops, conditionals) are based on simple statements (print, return, assign, pass). More complex nested structures from a single command are not yet supported.
*   **No Automated Tests.**
*   **State Management:** Basic.
*   **Error Handling:** Can be more robust.
*   **PySide6 Syntax Highlighting:** The current QSyntaxHighlighter is for Python only and has a basic implementation for multi-line docstrings. It does not use Pygments at runtime.

## Packaging for Windows with PySide6 & PyInstaller (Experimental)

This section provides basic instructions on how to package MyAppAgent as a standalone Windows executable using PyInstaller.

**Prerequisites:**
1.  Ensure Python 3.9+ is installed.
2.  Install PySide6: `pip install PySide6`
3.  Install PyInstaller: `pip install pyinstaller`

**Building the Executable:**
1.  Navigate to the `my_app_agent` project root directory.
2.  Run PyInstaller from this directory:
    ```bash
    pyinstaller --onefile --windowed --name MyAppAgent --icon=ui/myappagent.ico ui/main_ui_pyside.py
    ```
    *   `--onefile`: Bundles everything into a single executable.
    *   `--windowed`: Prevents a console window from opening when the GUI is run.
    *   `--name MyAppAgent`: Sets the name of the executable to `MyAppAgent.exe`.
    *   `--icon=ui/myappagent.ico`: Specifies the application icon (replace the placeholder).
    *   `ui/main_ui_pyside.py`: The entry point script for the PySide6 UI application.

3.  The executable (`MyAppAgent.exe`) will be found in a `dist` folder created in the `my_app_agent` directory.

**Considerations for PySide6 Applications:**
*   **Qt Libraries & Plugins:** PyInstaller has built-in support (hooks) for PySide6 and usually bundles the necessary Qt libraries and plugins automatically.
*   **Application Size:** PySide6 applications tend to be larger than equivalent Tkinter applications due to the Qt framework.
*   **Missing Plugins (Advanced):** In some complex cases or specific environments, PyInstaller might not automatically include all necessary Qt plugins (e.g., for platform-specific themes, image formats, SQL drivers). If you encounter issues like missing styles or functionalities in the packaged app, you might need to:
    *   Use a `.spec` file (generated by PyInstaller) to manually specify paths to Qt plugins using `datas` or `binaries` (e.g., `PySide6/plugins/platforms`, `PySide6/plugins/styles`).
    *   Use PyInstaller options like `--add-binary` or `--add-data`.
    This is typically not needed for simpler applications if PySide6 is installed correctly in the build environment.
*   **`generated_scripts` Directory:** The agent saves generated scripts to `YourUserDocuments/MyAppAgent/generated_scripts/`. This user-writable location is generally suitable for packaged applications.
*   **Application Icon:** Remember to replace the placeholder `my_app_agent/ui/myappagent.ico` with a proper `.ico` file before building for a professional look.

This provides a starting point for creating a distributable version of MyAppAgent.
```
