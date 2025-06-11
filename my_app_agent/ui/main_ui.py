# my_app_agent/ui/main_ui.py
import tkinter as tk
from tkinter import ttk # Import ttk
from tkinter import scrolledtext, font
import os
import sys

try:
    # Assumes my_app_agent is in PYTHONPATH or script is run from project root
    from my_app_agent.agent import AgentCore
except ImportError:
    # Fallback for running main_ui.py directly from the ui directory
    # This makes 'my_app_agent' directory (parent of 'ui') findable
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from agent import AgentCore

# Attempt to import Pygments
try:
    from pygments import lex
    from pygments.lexers import PythonLexer
    from pygments.token import Token # Import Token for easier access to token types
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False
    # UI will log this message in __init__ if needed


class MyAppAgentUI:
    def __init__(self, root_tk_window):
        self.root = root_tk_window
        self.root.title("MyAppAgent v0.7 - UI Polish") # Updated version
        self.root.geometry("950x750") # Slightly wider for two panes
        self.root.minsize(600, 400) # Set a minimum size

        self.agent_core = AgentCore()

        style = ttk.Style()
        available_themes = style.theme_names()
        # print(f"Available ttk themes: {available_themes}")
        # if 'vista' in available_themes: style.theme_use('vista')
        # elif 'clam' in available_themes: style.theme_use('clam')
        # else: style.theme_use(style.theme_use()) # Use current default

        # Platform-aware font selection
        self.default_font_family = "Arial"
        self.code_font_family = "Consolas"
        if sys.platform == "darwin": # macOS specific fonts
            self.default_font_family = "Helvetica Neue"
            self.code_font_family = "Menlo"
        elif sys.platform.startswith("linux"): # Linux specific fonts (example)
            self.default_font_family = "DejaVu Sans"
            self.code_font_family = "DejaVu Sans Mono"

        self.default_font = font.Font(family=self.default_font_family, size=10)
        self.text_font = font.Font(family=self.code_font_family, size=10) # Monospaced font

        # Configure default font for ttk widgets
        style.configure('.', font=self.default_font)
        style.configure('TButton', font=self.default_font)
        style.configure('TLabel', font=self.default_font)
        # ttk.Entry uses 'fieldfont' which might not be affected by '.' style.
        # We can set it directly or use a specific style for TEntry if needed.
        # For now, self.input_entry is explicitly given self.text_font.
        # style.configure('TEntry', font=self.text_font) # This might not work as expected for all themes

        # --- Top Frame for Context Labels ---
        context_frame = ttk.Frame(self.root, padding=(10, 5, 10, 5))
        context_frame.pack(fill=tk.X, side=tk.TOP)

        self.lang_label_text = tk.StringVar(value=f"Language: {self.agent_core.active_language}")
        lang_label = ttk.Label(context_frame, textvariable=self.lang_label_text)
        lang_label.pack(side=tk.LEFT, padx=(0,10))

        self.script_label_text = tk.StringVar(value=f"Script: {self.agent_core.current_script_name or 'None'}")
        script_label = ttk.Label(context_frame, textvariable=self.script_label_text)
        script_label.pack(side=tk.LEFT, padx=10)

        # --- Main Paned Window ---
        main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned_window.pack(expand=True, fill=tk.BOTH, padx=10, pady=(0,5))

        # --- Left Pane: Code View Area ---
        code_view_frame = ttk.Frame(main_paned_window, padding=5, relief="flat")
        code_view_label = ttk.Label(code_view_frame, text="Code View", font=(self.default_font_family, 10, "bold"))
        code_view_label.pack(side=tk.TOP, fill=tk.X, pady=(0,3))
        self.code_view_area = scrolledtext.ScrolledText(
            code_view_frame, wrap=tk.WORD, state=tk.DISABLED, font=self.text_font,
            relief=tk.SOLID, borderwidth=1 # Keep border on ScrolledText
        )
        self.code_view_area.pack(expand=True, fill=tk.BOTH)
        main_paned_window.add(code_view_frame, weight=1)

        # --- Right Pane: Log/Console Area ---
        log_view_frame = ttk.Frame(main_paned_window, padding=5, relief="flat")
        log_view_label = ttk.Label(log_view_frame, text="Log / Console", font=(self.default_font_family, 10, "bold"))
        log_view_label.pack(side=tk.TOP, fill=tk.X, pady=(0,3))
        self.log_area = scrolledtext.ScrolledText(
            log_view_frame, wrap=tk.WORD, state=tk.DISABLED, font=self.text_font,
            relief=tk.SOLID, borderwidth=1 # Keep border on ScrolledText
        )
        self.log_area.pack(expand=True, fill=tk.BOTH)
        main_paned_window.add(log_view_frame, weight=1)

        # --- Bottom Input Frame ---
        input_frame = ttk.Frame(self.root, padding=(10, 10, 10, 10))
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.input_entry = ttk.Entry(input_frame, font=self.text_font, width=70)
        # For ttk.Entry, font needs to be set via a style or it might use a default system font for entries.
        # Let's create a specific style for this ttk.Entry
        style.configure("Monospace.TEntry", font=self.text_font, padding=(3,3)) # Added internal padding via style
        self.input_entry.configure(style="Monospace.TEntry")
        self.input_entry.pack(side=tk.LEFT, padx=(0,10), expand=True, fill=tk.X) # Removed ipady, handle via style
        self.input_entry.bind("<Return>", self.on_send_command_event)

        self.send_button = ttk.Button(input_frame, text="Send", command=self.on_send_command, style="Accent.TButton")
        try:
            style.configure("Accent.TButton", font=self.default_font, padding=(5,2))
        except tk.TclError: # Style "Accent.TButton" might not exist on all themes/platforms
            style.configure("Send.TButton", font=self.default_font, padding=(5,2)) # Fallback style name
            self.send_button.configure(style="Send.TButton")
        self.send_button.pack(side=tk.RIGHT)

        self.setup_tags()
        if not PYGMENTS_AVAILABLE: self.add_log_message("Pygments library not found. Syntax highlighting disabled.", "error_message")
        self.add_log_message("Welcome to MyAppAgent! UI Refined.", tag="info_message")
        self._update_code_view(script_content="// Python code will appear here.")
        self.input_entry.focus_set()


    def setup_tags(self):
        # Log area tags
        self.log_area.tag_configure("info_message", foreground="blue", font=self.default_font)
        self.log_area.tag_configure("error_message", foreground="red", font=(self.default_font.cget("family"), self.default_font.cget("size"), "bold"))
        self.log_area.tag_configure("success_message", foreground="green", font=self.default_font)
        self.log_area.tag_configure("clarification_message", foreground="#9B59B6", font=self.default_font) # Purple
        self.log_area.tag_configure("user_input", foreground="#555555", font=self.text_font)
        self.log_area.tag_configure("agent_response_default", foreground="black", font=self.default_font)
        self.log_area.tag_configure("debug_info", foreground="orange", font=(self.text_font.cget("family"), 8))

        # Code view tags
        base_code_fg = "#222222"
        self.code_view_area.tag_configure("code_default", font=self.text_font, foreground=base_code_fg)
        self.code_view_area.tag_configure("code_error", foreground="red", font=self.text_font)

        if PYGMENTS_AVAILABLE:
            self.code_view_area.tag_configure(str(Token.Keyword), foreground="#0000ff")
            self.code_view_area.tag_configure(str(Token.Keyword.Constant), foreground="#0000ff")
            self.code_view_area.tag_configure(str(Token.Keyword.Declaration), foreground="#0000ff")
            self.code_view_area.tag_configure(str(Token.Keyword.Namespace), foreground="#0000ff", font=(self.code_font_family, self.text_font.cget("size"), "bold"))
            self.code_view_area.tag_configure(str(Token.Keyword.Pseudo), foreground="#0000ff")
            self.code_view_area.tag_configure(str(Token.Keyword.Type), foreground="#0000ff")
            self.code_view_area.tag_configure(str(Token.Name.Class), foreground="#2b91af", font=(self.code_font_family, self.text_font.cget("size"), "bold"))
            self.code_view_area.tag_configure(str(Token.Name.Function), foreground="#2b91af")
            self.code_view_area.tag_configure(str(Token.Name.Builtin), foreground="#2b91af")
            self.code_view_area.tag_configure(str(Token.Name.Builtin.Pseudo), foreground="#0000ff", font=(self.code_font_family, self.text_font.cget("size"), "bold")) # self
            self.code_view_area.tag_configure(str(Token.Name.Decorator), foreground="#2b91af", font=(self.code_font_family, self.text_font.cget("size"), "italic"))
            self.code_view_area.tag_configure(str(Token.Name.Exception), foreground="#9b2323", font=(self.code_font_family, self.text_font.cget("size"), "bold"))
            self.code_view_area.tag_configure(str(Token.Name), foreground="#1f7199")
            self.code_view_area.tag_configure(str(Token.Literal.String), foreground="#a31515")
            self.code_view_area.tag_configure(str(Token.Literal.String.Doc), foreground="#4F5D95", font=(self.code_font_family, self.text_font.cget("size"), "italic"))
            self.code_view_area.tag_configure(str(Token.Literal.Number.Integer), foreground="#098658")
            self.code_view_area.tag_configure(str(Token.Literal.Number.Float), foreground="#098658")
            self.code_view_area.tag_configure(str(Token.Literal.Number), foreground="#098658")
            self.code_view_area.tag_configure(str(Token.Operator), foreground="#707070")
            self.code_view_area.tag_configure(str(Token.Punctuation), foreground="#707070")
            self.code_view_area.tag_configure(str(Token.Comment), foreground="#008000")
            self.code_view_area.tag_configure(str(Token.Comment.Single), foreground="#008000")
            self.code_view_area.tag_configure(str(Token.Text), foreground=base_code_fg)
            self.code_view_area.tag_configure(str(Token.Error), background="red", foreground="white")


    def add_log_message(self, message: str, tag: str = None, on_new_line: bool = True):
        self.log_area.config(state=tk.NORMAL)
        if on_new_line and self.log_area.index('end-1c') != "1.0": self.log_area.insert(tk.END, "\n")
        self.log_area.insert(tk.END, str(message) if message is not None else "", tag if tag else "agent_response_default")
        self.log_area.see(tk.END); self.log_area.config(state=tk.DISABLED)

    def _update_code_view(self, script_path: str = None, script_content: str = None):
        self.code_view_area.config(state=tk.NORMAL); self.code_view_area.delete('1.0', tk.END)
        content_to_display = None
        if script_path:
            try:
                with open(script_path, "r") as f: content_to_display = f.read()
            except FileNotFoundError: self.code_view_area.insert(tk.END, f"// Error: Could not find script {script_path}", "code_error")
            except Exception as e: self.code_view_area.insert(tk.END, f"// Error reading script {script_path}: {e}", "code_error")
        elif script_content is not None: content_to_display = script_content

        if content_to_display is None and script_path : # Error already printed by try/except
            self.code_view_area.config(state=tk.DISABLED); self.code_view_area.see("1.0"); return
        if content_to_display is None : content_to_display = "// No active script or script content to display."

        if PYGMENTS_AVAILABLE and self.agent_core.active_language == "python" and content_to_display and not content_to_display.startswith("// Error:") :
            lexer = PythonLexer()
            for token_type, value in lex(content_to_display, lexer):
                tag_to_apply = str(token_type); current_type = token_type
                while not self.code_view_area.tag_cget(tag_to_apply, "foreground") and current_type.parent:
                    current_type = current_type.parent; tag_to_apply = str(current_type)
                if not self.code_view_area.tag_cget(tag_to_apply, "foreground"): tag_to_apply = "code_default"
                self.code_view_area.insert(tk.END, value, tag_to_apply)
        else: self.code_view_area.insert(tk.END, content_to_display, "code_default" if not content_to_display.startswith("// Error:") else "code_error")
        self.code_view_area.config(state=tk.DISABLED); self.code_view_area.see("1.0")

    def on_send_command(self):
        user_input = self.input_entry.get()
        if not user_input.strip(): return
        self.add_log_message(f"> {user_input}", tag="user_input")
        self.input_entry.delete(0, tk.END); self.input_entry.focus_set()
        results = self.agent_core.process_command(user_input)
        response_tag = "agent_response_default"
        if results.get("status") == "error": response_tag = "error_message"
        elif results.get("status") == "success": response_tag = "success_message"
        elif results.get("status") == "clarification_needed": response_tag = "clarification_message"
        if results.get("main_response"): self.add_log_message(results["main_response"], tag=response_tag)
        if results.get("debug_info"): self.add_log_message(f"DEBUG: {results['debug_info']}", tag="debug_info")
        if results.get("script_to_display_path"): self._update_code_view(script_path=results["script_to_display_path"])
        elif not results.get("current_script_name"): self._update_code_view(script_content="// No active script or script content to display.")
        self.lang_label_text.set(f"Language: {results['active_language']}")
        self.script_label_text.set(f"Script: {results['current_script_name'] or 'None'}")
        self.root.update_idletasks()


    def on_send_command_event(self, event): self.on_send_command(); return "break"

if __name__ == "__main__":
    app_root_window = tk.Tk()
    ui = MyAppAgentUI(app_root_window)
    app_root_window.mainloop()
