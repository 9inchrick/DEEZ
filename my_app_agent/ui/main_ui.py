# my_app_agent/ui/main_ui.py
# This file will contain the main Tkinter UI application logic for MyAppAgent.
import tkinter as tk
from tkinter import scrolledtext, font
import os # For reading script files if needed by UI
import sys

# Adjust path to import AgentCore from the parent directory's 'agent' module
# This is a common way to handle imports when running a submodule directly.
# For a packaged application, this might be handled differently.
try:
    from my_app_agent.agent import AgentCore
except ImportError:
    # Fallback if running main_ui.py directly from the ui directory
    # This assumes 'my_app_agent' is the parent of 'ui'
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    # Now try importing assuming my_app_agent is in the path
    from my_app_agent.agent import AgentCore


class MyAppAgentUI:
    def __init__(self, root_tk_window): # Renamed root to root_tk_window for clarity
        self.root = root_tk_window
        self.root.title("MyAppAgent v0.4 - UI Connected") # Updated title
        self.root.geometry("800x600")

        self.agent_core = AgentCore() # Instantiate AgentCore

        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Arial", size=10)
        self.text_font = font.Font(family="Consolas", size=10)

        context_frame = tk.Frame(self.root, pady=5)
        context_frame.pack(fill=tk.X, side=tk.TOP)

        self.lang_label_text = tk.StringVar(value=f"Language: {self.agent_core.active_language}")
        lang_label = tk.Label(context_frame, textvariable=self.lang_label_text, font=self.default_font)
        lang_label.pack(side=tk.LEFT, padx=10)

        self.script_label_text = tk.StringVar(value=f"Script: {self.agent_core.current_script_name or 'None'}")
        script_label = tk.Label(context_frame, textvariable=self.script_label_text, font=self.default_font)
        script_label.pack(side=tk.LEFT, padx=10)

        self.log_area = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, state=tk.DISABLED, font=self.text_font,
            relief=tk.SOLID, borderwidth=1
        )
        self.log_area.pack(padx=10, pady=(0,5), expand=True, fill=tk.BOTH)

        input_frame = tk.Frame(self.root, pady=5)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.input_entry = tk.Entry(input_frame, font=self.text_font, width=70)
        self.input_entry.pack(side=tk.LEFT, padx=(10,5), expand=True, fill=tk.X)
        self.input_entry.bind("<Return>", self.on_send_command_event)

        self.send_button = tk.Button(
            input_frame, text="Send", command=self.on_send_command,
            font=self.default_font, relief=tk.RAISED
        )
        self.send_button.pack(side=tk.RIGHT, padx=(0,10))

        self.setup_tags()
        self.add_log_message("Welcome to MyAppAgent! Type your commands below.", tag="info_message")


    def setup_tags(self):
        self.log_area.tag_configure("info_message", foreground="blue")
        self.log_area.tag_configure("error_message", foreground="red", font=(self.text_font.cget("family"), self.text_font.cget("size"), "bold"))
        self.log_area.tag_configure("success_message", foreground="green")
        self.log_area.tag_configure("clarification_message", foreground="#9B59B6") # Purple
        self.log_area.tag_configure("user_input", foreground="#555555", font=(self.text_font.cget("family"), self.text_font.cget("size"), "italic")) # Dark gray italic
        self.log_area.tag_configure("agent_response_default", foreground="black")
        self.log_area.tag_configure("debug_info", foreground="#F39C12", font=(self.text_font.cget("family"), 8)) # Orange, smaller
        self.log_area.tag_configure("script_content_header", foreground="#2C3E50", font=(self.default_font.cget("family"), self.default_font.cget("size"), "bold")) # Dark blue/gray
        self.log_area.tag_configure("script_content_body", foreground="#34495E", font=self.text_font) # Darker gray/blue

    def add_log_message(self, message: str, tag: str = None, on_new_line: bool = True):
        self.log_area.config(state=tk.NORMAL)
        if on_new_line and self.log_area.index('end-1c') != "1.0": # Add newline if not the first character in the text area
            self.log_area.insert(tk.END, "\n")

        # Ensure message is a string, as None or other types might cause issues
        if message is None:
            message = ""

        self.log_area.insert(tk.END, str(message), tag if tag else "agent_response_default")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def _display_script_in_log(self, script_path: str):
        self.add_log_message(f"--- Content of {os.path.basename(script_path)} ---", tag="script_content_header")
        try:
            with open(script_path, "r") as f:
                content = f.read()
            # Add message line by line to allow for future line-based processing if needed
            # And to ensure each line gets the correct tag if added individually.
            if content.strip(): # Only add content if not empty
                for line in content.splitlines():
                     self.add_log_message(line, tag="script_content_body", on_new_line=True) # Each line of script on new line
            else:
                 self.add_log_message("[Empty script]", tag="script_content_body", on_new_line=True)
        except Exception as e:
            self.add_log_message(f"Error reading script {script_path}: {e}", tag="error_message")
        self.add_log_message(f"--- End of {os.path.basename(script_path)} ---", tag="script_content_header")

    def on_send_command(self):
        user_input = self.input_entry.get()
        if not user_input.strip():
            return

        self.add_log_message(f"> {user_input}", tag="user_input")
        self.input_entry.delete(0, tk.END)
        self.input_entry.focus_set() # Return focus to input entry

        # Call AgentCore
        results = self.agent_core.process_command(user_input)

        # Determine response tag based on status
        response_tag = "agent_response_default" # Default
        status = results.get("status")
        if status == "error":
            response_tag = "error_message"
        elif status == "success": # Generic success, specific messages might override
            response_tag = "success_message"
        elif status == "clarification_needed":
            response_tag = "clarification_message"

        if results.get("main_response"):
            self.add_log_message(results["main_response"], tag=response_tag)

        if results.get("debug_info"): # Check if debug_info is not empty
            self.add_log_message(f"DEBUG: {results['debug_info']}", tag="debug_info")

        if results.get("script_to_display_path"):
            self._display_script_in_log(results["script_to_display_path"])

        # Update context labels
        self.lang_label_text.set(f"Language: {results['active_language']}")
        self.script_label_text.set(f"Script: {results['current_script_name'] or 'None'}")
        self.root.update_idletasks() # Ensure UI updates are processed


    def on_send_command_event(self, event):
        self.on_send_command()
        return "break" # Prevents the default Enter key behavior (like adding a newline)


if __name__ == "__main__":
    app_root_window = tk.Tk()
    ui = MyAppAgentUI(app_root_window)
    # To make input field active on start:
    ui.input_entry.focus_set()
    app_root_window.mainloop()
