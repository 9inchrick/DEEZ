# MyAppAgent - An App Building Agent

MyAppAgent is a conversational agent designed to assist in building applications.
This is an early-stage project focusing on understanding user requests in natural
language and generating code, with a PySide6 graphical user interface.

## Requirements

*   **Python 3.9 or newer is required.** (Due to `ast.unparse`).
*   **PySide6:** For the graphical user interface. Install using: `pip install PySide6`

## Current Capabilities

As of the current version, MyAppAgent can:

*   Engage in a basic text-based conversation (CLI or GUI) to understand commands.
*   Manage a context of the "active language" (Python and experimental JavaScript).
*   Manage a context of the "current script" being worked on.
*   **Python Code Generation (requires Python 3.9+):**
    *   Create new Python script files (`.py`) in `~/Documents/MyAppAgent/generated_scripts/python/`.
    *   Delete existing Python scripts from this directory via UI.
    *   Add new, empty functions, methods (including `self` and multi-statement bodies), class attributes, instance attributes (in `__init__`), and properties (with getters, setters, deleters, and `__init__` integration) to Python scripts.
    *   Add simple `print`, `return`, `if/elif/else`, `for` loops, `while` loops, `try-except-else-finally` blocks, and basic file operations (`with open(...)`) to functions or methods. Multi-statement bodies (delimited by " then ") are supported for these structures.
    *   Add decorators to functions and methods.
    *   Add `import` and `from ... import ...` statements.
    *   Create new, empty classes, including support for inheritance from base classes.
    *   Prevent overwriting existing scripts and name clashes where applicable.
*   **JavaScript Code Generation (Experimental):**
    *   Create new JavaScript script files (`.js`) in `~/Documents/MyAppAgent/generated_scripts/javascript/`.
    *   Delete existing JavaScript scripts from this directory via UI.
*   Display the generated/modified code to the user.
*   **PySide6 Graphical User Interface:**
    *   A three-pane layout: File Navigator, Code View, and Log/Console.
    *   File navigator to browse and open generated scripts.
    *   **Context menu in File Navigator** to delete scripts (with confirmation).
    *   **"+ New Script" button** in the UI to create Python or JavaScript files via dialogs.
    *   Python syntax highlighting in the Code View using `QSyntaxHighlighter`.
    *   Dark theme implemented using QSS.

## How to Run

1.  Ensure you have **Python 3.9 or newer** installed.
2.  Install PySide6: `pip install PySide6`
3.  Navigate to the `my_app_agent` project root directory.
4.  **To run the GUI application (recommended):**
    ```bash
    python ui/main_ui_pyside.py
    ```
    *   Use the "+ New Script" button or right-click in the File Navigator pane for script operations.
    *   Double-click files in the File Navigator to open them in the Code View.
5.  **To run the command-line interface (for testing core logic):**
    ```bash
    python agent.py
    ```
6.  Generated scripts are saved by default in your `Documents/MyAppAgent/generated_scripts/` directory (under `python` or `javascript` subfolders).

## Project Structure
# ... (Project Structure remains the same as last update, already includes ui/main_ui_pyside.py)
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
├── generated_scripts/          # (This directory is created in ~/Documents/MyAppAgent/)
│   ├── python/
│   └── javascript/
└── README.md                   # This file
```

## Known Limitations & Future Work
# ... (Known Limitations remain largely the same, minor wording tweaks if needed)
*   **Language Support:** Python is primary. JavaScript support is basic (create/delete files).
*   **NLU Robustness:** Regex-based NLU has limitations.
*   **Code Complexity:** Generated code structures are still relatively simple.
*   **No Automated Tests.**
*   **State Management:** Basic.
*   **Error Handling:** Can be more robust.
*   **PySide6 Syntax Highlighting:** Python only; multi-line docstring basic.
*   **File Navigator:** Currently relies on `QFileSystemModel`'s default behavior for auto-refreshing on external changes, which can sometimes have delays or inconsistencies across platforms. More explicit refresh mechanisms could be added if needed.

## Packaging for Windows with PySide6 & PyInstaller (Experimental)
# ... (Packaging section remains the same as last update)
This section provides basic instructions on how to package MyAppAgent as a standalone Windows executable using PyInstaller.

**Prerequisites:**
1.  Ensure Python 3.9+ is installed.
2.  Install PySide6: `pip install PySide6`
3.  Install PyInstaller: `pip install pyinstaller`

**Building the Executable:**
1.  Navigate to the `my_app_agent` project root directory.
2.  Run PyInstaller:
    ```bash
    pyinstaller --onefile --windowed --name MyAppAgent --icon=ui/myappagent.ico ui/main_ui_pyside.py
    ```
    *   `--onefile`: Bundles everything into a single executable.
    *   `--windowed`: Prevents a console window from opening when the GUI is run.
    *   `--name MyAppAgent`: Sets the name of the executable to `MyAppAgent.exe`.
    *   `--icon=ui/myappagent.ico`: Specifies the application icon (replace the placeholder).
    *   `ui/main_ui_pyside.py`: The entry point script for the PySide6 UI application.

3.  The executable (`MyAppAgent.exe`) will be found in a `dist` folder.

**Considerations for PySide6 Applications:**
*   **Qt Libraries & Plugins:** PyInstaller usually bundles necessary Qt libraries. For issues, manual intervention in the `.spec` file or options like `--add-binary` for plugins (e.g., `PySide6/plugins/platforms`) might be needed.
*   **Application Size:** PySide6 apps are larger than Tkinter ones.
*   **`generated_scripts` Directory:** Saved to `YourUserDocuments/MyAppAgent/generated_scripts/`.
*   **Application Icon:** Replace `my_app_agent/ui/myappagent.ico` with a proper `.ico` file.
```
