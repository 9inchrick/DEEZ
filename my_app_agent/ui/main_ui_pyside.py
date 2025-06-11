import sys
import os
from PySide6 import QtWidgets, QtCore, QtGui

# Adjust path to import AgentCore
try:
    from my_app_agent.agent import AgentCore
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from my_app_agent.agent import AgentCore

DARK_THEME_QSS = """
QMainWindow, QWidget { background-color: #2B2B2B; color: #BBBBBB; }
QTextEdit { background-color: #1E1E1E; color: #D4D4D4; border: 1px solid #3E3E3E; font-family: Consolas, "DejaVu Sans Mono", "Courier New", monospace; font-size: 10pt; }
QLineEdit { background-color: #3C3C3C; color: #D4D4D4; border: 1px solid #555555; padding: 3px; font-family: Consolas, "DejaVu Sans Mono", "Courier New", monospace; font-size: 10pt; }
QPushButton { background-color: #555555; color: #FFFFFF; border: 1px solid #666666; padding: 5px 8px; min-height: 1.5em; font-family: Arial, "Helvetica Neue", "DejaVu Sans", sans-serif; font-size: 9pt; }
QPushButton:hover { background-color: #6A6A6A; } QPushButton:pressed { background-color: #4A4A4A; }
QLabel { color: #BBBBBB; font-family: Arial, "Helvetica Neue", "DejaVu Sans", sans-serif; font-size: 9pt; }
QSplitter::handle { background-color: #3E3E3E; border: 1px solid #2B2B2B; }
QSplitter::handle:horizontal { width: 5px; } QSplitter::handle:vertical { height: 5px; }
QTreeView { background-color: #1E1E1E; color: #D4D4D4; border: 1px solid #3E3E3E; alternate-background-color: #252525; font-family: Arial, "Helvetica Neue", "DejaVu Sans", sans-serif; font-size: 9pt; }
QTreeView::item:selected { background-color: #007ACC; color: white; }
QHeaderView::section { background-color: #3E3E3E; color: #BBBBBB; padding: 4px; border: 1px solid #2B2B2B; font-family: Arial, "Helvetica Neue", "DejaVu Sans", sans-serif; font-size: 9pt; }
QScrollBar:vertical { border: 1px solid #3E3E3E; background: #2B2B2B; width: 12px; margin: 0px; }
QScrollBar::handle:vertical { background: #555555; min-height: 20px; border-radius: 6px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal { border: 1px solid #3E3E3E; background: #2B2B2B; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: #555555; min-width: 20px; border-radius: 6px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { border: none; background: none; width: 0px; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
"""

class PythonSyntaxHighlighter(QtGui.QSyntaxHighlighter): # ... (as before)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
        keyword_format = QtGui.QTextCharFormat(); keyword_format.setForeground(QtGui.QColor("#569CD6")); keyword_format.setFontWeight(QtGui.QFont.Weight.Bold)
        keywords = ["\\bdef\\b", "\\bclass\\b", "\\bif\\b", "\\belif\\b", "\\belse\\b", "\\bfor\\b", "\\bin\\b", "\\bwhile\\b", "\\btry\\b", "\\bexcept\\b", "\\bfinally\\b", "\\bpass\\b", "\\bbreak\\b", "\\bcontinue\\b", "\\breturn\\b", "\\byield\\b", "\\bimport\\b", "\\bfrom\\b", "\\bas\\b", "\\bwith\\b", "\\bassert\\b", "\\bdel\\b", "\\bglobal\\b", "\\bnonlocal\\b", "\\blambda\\b", "\\bis\\b", "\\bnot\\b", "\\band\\b", "\\bor\\b"]
        for word in keywords: self.highlighting_rules.append({'pattern': QtCore.QRegularExpression(word), 'format': keyword_format, 'group': 0})
        pseudo_keywords_format = QtGui.QTextCharFormat(); pseudo_keywords_format.setForeground(QtGui.QColor("#C586C0")); pseudo_keywords_format.setFontWeight(QtGui.QFont.Weight.Bold)
        pseudo_keywords = ["\\bNone\\b", "\\bTrue\\b", "\\bFalse\\b", "\\bself\\b", "\\bcls\\b"]
        for word in pseudo_keywords: self.highlighting_rules.append({'pattern': QtCore.QRegularExpression(word), 'format': pseudo_keywords_format, 'group': 0})
        class_def_format = QtGui.QTextCharFormat(); class_def_format.setForeground(QtGui.QColor("#4EC9B0")); class_def_format.setFontWeight(QtGui.QFont.Weight.Bold)
        self.highlighting_rules.append({'pattern': QtCore.QRegularExpression("\\bclass\\s+([A-Za-z_][A-Za-z0-9_]*)"), 'format': class_def_format, 'group': 1})
        func_def_format = QtGui.QTextCharFormat(); func_def_format.setForeground(QtGui.QColor("#DCDCAA"))
        self.highlighting_rules.append({'pattern': QtCore.QRegularExpression("\\bdef\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*\\("), 'format': func_def_format, 'group': 1})
        decorator_format = QtGui.QTextCharFormat(); decorator_format.setForeground(QtGui.QColor("#DCDCAA")); decorator_format.setFontItalic(True)
        self.highlighting_rules.append({'pattern': QtCore.QRegularExpression("@[A-Za-z0-9_.]+"), 'format': decorator_format, 'group': 0})
        string_format = QtGui.QTextCharFormat(); string_format.setForeground(QtGui.QColor("#CE9178"))
        self.highlighting_rules.append({'pattern': QtCore.QRegularExpression("'.*?'"), 'format': string_format, 'group': 0})
        self.highlighting_rules.append({'pattern': QtCore.QRegularExpression("\".*?\""), 'format': string_format, 'group': 0})
        self.docstring_format = QtGui.QTextCharFormat(); self.docstring_format.setForeground(QtGui.QColor("#6A9955")); self.docstring_format.setFontItalic(True)
        self.tri_single_start_expression = QtCore.QRegularExpression("'''"); self.tri_double_start_expression = QtCore.QRegularExpression("\"\"\"")
        self.tri_single_end_expression = QtCore.QRegularExpression("'''"); self.tri_double_end_expression = QtCore.QRegularExpression("\"\"\"")
        comment_format = QtGui.QTextCharFormat(); comment_format.setForeground(QtGui.QColor("#6A9955")); comment_format.setFontItalic(True)
        self.highlighting_rules.append({'pattern': QtCore.QRegularExpression("#[^\\n]*"), 'format': comment_format, 'group': 0})
        number_format = QtGui.QTextCharFormat(); number_format.setForeground(QtGui.QColor("#B5CEA8"))
        self.highlighting_rules.append({'pattern': QtCore.QRegularExpression("\\b[0-9]+\\.?[0-9]*[eE]?[-+]?[0-9]*\\b"), 'format': number_format, 'group': 0})
        self.highlighting_rules.append({'pattern': QtCore.QRegularExpression("\\b0[xX][0-9a-fA-F]+\\b"), 'format': number_format, 'group': 0})

    def highlightBlock(self, text): # ... (as before)
        for rule in self.highlighting_rules:
            expression = rule['pattern']; it = expression.globalMatch(text)
            while it.hasNext():
                match = it.next(); start = match.capturedStart(rule['group']); length = match.capturedLength(rule['group'])
                if start >= 0 : self.setFormat(start, length, rule['format'])
        self.setCurrentBlockState(0)
        # Multi-line string handling (simplified)
        current_block_state_for_single = 0; current_block_state_for_double = 0
        if self.previousBlockState() == 1 : current_block_state_for_single = 1
        if self.previousBlockState() == 2 : current_block_state_for_double = 1

        # Triple single quotes
        startIndex = 0
        if current_block_state_for_single == 0: match = self.tri_single_start_expression.match(text); startIndex = match.capturedStart() if match.hasMatch() else -1
        while startIndex >= 0:
            match_end = self.tri_single_end_expression.match(text, startIndex + (3 if current_block_state_for_single == 0 else 0) ) # if already in state, end can be at start
            endIndex = match_end.capturedStart() if match_end.hasMatch() else -1
            length = 0
            if endIndex == -1: self.setCurrentBlockState(1); length = len(text) - startIndex
            else: length = endIndex - startIndex + 3
            self.setFormat(startIndex, length, self.docstring_format)
            match_next_start = self.tri_single_start_expression.match(text, startIndex + length)
            startIndex = match_next_start.capturedStart() if match_next_start.hasMatch() else -1
            current_block_state_for_single = 0 # Reset after finding a start or finishing one

        # Triple double quotes
        startIndex = 0
        if current_block_state_for_double == 0: match = self.tri_double_start_expression.match(text); startIndex = match.capturedStart() if match.hasMatch() else -1
        while startIndex >= 0:
            match_end = self.tri_double_end_expression.match(text, startIndex + (3 if current_block_state_for_double == 0 else 0))
            endIndex = match_end.capturedStart() if match_end.hasMatch() else -1
            length = 0
            if endIndex == -1: self.setCurrentBlockState(2); length = len(text) - startIndex
            else: length = endIndex - startIndex + 3
            self.setFormat(startIndex, length, self.docstring_format)
            match_next_start = self.tri_double_start_expression.match(text, startIndex + length)
            startIndex = match_next_start.capturedStart() if match_next_start.hasMatch() else -1
            current_block_state_for_double = 0


class MyAppAgentPysideUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.agent_core = AgentCore()
        self.setWindowTitle("MyAppAgent v0.9 - New Script UI")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)
        self.init_fonts_and_styles()
        self.init_ui()
        self._update_context_labels()
        self._add_log_message("Welcome to MyAppAgent! File Navigator and New Script added.", color="cyan", is_html=True)
        self._update_code_view_area(script_content="// Select or create a file to begin.")
        self.input_entry.setFocus()

    def init_fonts_and_styles(self): # ... (as before)
        self.default_font_family = "Arial"; self.code_font_family = "Consolas"
        if sys.platform == "darwin": self.default_font_family = "Helvetica Neue"; self.code_font_family = "Menlo"
        elif sys.platform.startswith("linux"): self.default_font_family = "DejaVu Sans"; self.code_font_family = "DejaVu Sans Mono"
        self.default_font = QtGui.QFont(self.default_font_family, 9); self.code_view_font = QtGui.QFont(self.code_font_family, 10); self.log_font = QtGui.QFont(self.code_font_family, 9); self.input_font = QtGui.QFont(self.code_font_family, 10)

    def init_ui(self):
        central_widget = QtWidgets.QWidget(); self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget); main_layout.setContentsMargins(5,5,5,5)
        context_widget = QtWidgets.QWidget(); context_layout = QtWidgets.QHBoxLayout(context_widget); context_layout.setContentsMargins(0,0,0,0)
        self.lang_label = QtWidgets.QLabel(); self.script_label = QtWidgets.QLabel()
        self.lang_label.setFont(self.default_font); self.script_label.setFont(self.default_font)
        context_layout.addWidget(self.lang_label); context_layout.addWidget(self.script_label); context_layout.addStretch(); main_layout.addWidget(context_widget)

        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal); main_layout.addWidget(self.main_splitter)

        file_nav_container = QtWidgets.QFrame(); file_nav_container.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        file_nav_layout = QtWidgets.QVBoxLayout(file_nav_container); file_nav_layout.setContentsMargins(2,2,2,2)

        file_nav_header_layout = QtWidgets.QHBoxLayout() # For label and button
        file_nav_label = QtWidgets.QLabel("File Navigator"); file_nav_label.setFont(QtGui.QFont(self.default_font_family, 10, QtGui.QFont.Weight.Bold))
        file_nav_header_layout.addWidget(file_nav_label)
        file_nav_header_layout.addStretch()
        self.new_script_button = QtWidgets.QPushButton("+ New Script")
        self.new_script_button.setFont(self.default_font)
        self.new_script_button.clicked.connect(self.on_new_script_requested)
        file_nav_header_layout.addWidget(self.new_script_button)
        file_nav_layout.addLayout(file_nav_header_layout)

        self.file_navigator_tree = QtWidgets.QTreeView(); self.file_system_model = QtWidgets.QFileSystemModel()
        self.scripts_base_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'MyAppAgent', 'generated_scripts')
        os.makedirs(os.path.join(self.scripts_base_dir, "python"), exist_ok=True); os.makedirs(os.path.join(self.scripts_base_dir, "javascript"), exist_ok=True)
        self.file_system_model.setRootPath(self.scripts_base_dir); self.file_system_model.setNameFilters(["*.py", "*.js"]); self.file_system_model.setNameFilterDisables(False)
        self.file_navigator_tree.setModel(self.file_system_model); self.file_navigator_tree.setRootIndex(self.file_system_model.index(self.scripts_base_dir))
        for i in range(1,4): self.file_navigator_tree.setColumnHidden(i, True)
        self.file_navigator_tree.doubleClicked.connect(self.on_file_selected); self.file_navigator_tree.setHeaderHidden(True)
        self.file_navigator_tree.setFont(QtGui.QFont(self.default_font_family, 9))
        file_nav_layout.addWidget(self.file_navigator_tree); self.main_splitter.addWidget(file_nav_container)

        right_side_container = QtWidgets.QWidget(); right_side_layout = QtWidgets.QVBoxLayout(right_side_container); right_side_layout.setContentsMargins(0,0,0,0)
        self.code_log_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical); right_side_layout.addWidget(self.code_log_splitter)
        code_view_container = QtWidgets.QFrame(); code_view_container.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        cv_layout = QtWidgets.QVBoxLayout(code_view_container); cv_layout.setContentsMargins(2,2,2,2)
        cv_label = QtWidgets.QLabel("Code View"); cv_label.setFont(QtGui.QFont(self.default_font_family, 10, QtGui.QFont.Weight.Bold)); cv_layout.addWidget(cv_label)
        self.code_view_area = QtWidgets.QTextEdit(); self.code_view_area.setReadOnly(True); self.code_view_area.setFont(self.code_view_font)
        self.python_highlighter = PythonSyntaxHighlighter(self.code_view_area.document())
        cv_layout.addWidget(self.code_view_area); self.code_log_splitter.addWidget(code_view_container)
        log_view_container = QtWidgets.QFrame(); log_view_container.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        lv_layout = QtWidgets.QVBoxLayout(log_view_container); lv_layout.setContentsMargins(2,2,2,2)
        lv_label = QtWidgets.QLabel("Log / Console"); lv_label.setFont(QtGui.QFont(self.default_font_family, 10, QtGui.QFont.Weight.Bold)); lv_layout.addWidget(lv_label)
        self.log_area = QtWidgets.QTextEdit(); self.log_area.setReadOnly(True); self.log_area.setFont(self.log_font)
        lv_layout.addWidget(self.log_area); self.code_log_splitter.addWidget(log_view_container)
        self.code_log_splitter.setSizes([int(self.geometry().height() * 0.6), int(self.geometry().height() * 0.4)])
        self.main_splitter.addWidget(right_side_container); self.main_splitter.setSizes([int(self.geometry().width() * 0.25), int(self.geometry().width() * 0.75)])
        input_widget = QtWidgets.QWidget(); input_layout = QtWidgets.QHBoxLayout(input_widget); input_layout.setContentsMargins(5,5,5,5)
        self.input_entry = QtWidgets.QLineEdit(); self.input_entry.setFont(self.input_font)
        self.input_entry.returnPressed.connect(self.on_send_command)
        self.send_button = QtWidgets.QPushButton("Send"); self.send_button.setFont(self.default_font)
        self.send_button.clicked.connect(self.on_send_command)
        input_layout.addWidget(self.input_entry); input_layout.addWidget(self.send_button)
        main_layout.addWidget(input_widget)

    def on_new_script_requested(self):
        languages = ["Python", "JavaScript"]
        language_chosen, ok = QtWidgets.QInputDialog.getItem(self, "New Script Language",
                                                             "Select language:", languages, 0, False)
        if ok and language_chosen:
            filename_base = "new_script"
            extension = ".py" if language_chosen == "Python" else ".js"

            filename, ok = QtWidgets.QInputDialog.getText(self, "New Script Name",
                                                          f"Enter filename for {language_chosen} script (e.g., {filename_base}{extension}):",
                                                          QtWidgets.QLineEdit.EchoMode.Normal,
                                                          f"{filename_base}{extension}")
            if ok and filename:
                filename = filename.strip()
                if not filename:
                    QtWidgets.QMessageBox.warning(self, "Input Error", "Filename cannot be empty.")
                    return

                # Ensure correct extension
                if language_chosen == "Python" and not filename.endswith(".py"):
                    filename += ".py"
                elif language_chosen == "JavaScript" and not filename.endswith(".js"):
                    filename += ".js"

                # Call AgentCore method (to be created in agent.py)
                results = self.agent_core.handle_ui_create_script(filename, language_chosen.lower())

                self._add_log_message(results.get("main_response", "Error processing new script request."),
                                      color="red" if results.get("status") == "error" else "green")

                if results.get("status") == "success":
                    self._update_code_view_area(script_path=results.get("script_to_display_path"))
                    self.agent_core.active_language = results["active_language"]
                    self.agent_core.current_script_name = results["current_script_name"]
                    self._update_context_labels()
                    # Refresh file navigator - QFileSystemModel should auto-update on directory changes.
                    # If not, a more explicit refresh might be needed, but often it's automatic.
                    # Forcing a re-evaluation of the root path can sometimes help if needed:
                    # current_root = self.file_system_model.rootPath()
                    # self.file_system_model.setRootPath("") # This might collapse tree
                    # self.file_system_model.setRootPath(current_root)
                    # self.file_navigator_tree.setRootIndex(self.file_system_model.index(current_root))

            else: # User cancelled filename input
                 self._add_log_message("New script name cancelled.", color="gray")
        else: # User cancelled language selection
            self._add_log_message("New script language selection cancelled.", color="gray")


    def on_file_selected(self, index: QtCore.QModelIndex): # ... (as before)
        file_path = self.file_system_model.filePath(index)
        if not self.file_system_model.isDir(index) and os.path.isfile(file_path):
            self._update_code_view_area(script_path=file_path)
            file_name = os.path.basename(file_path)
            self.agent_core.current_script_name = file_name
            lang = "python" if file_name.endswith(".py") else "javascript" if file_name.endswith(".js") else self.agent_core.active_language
            self.agent_core.active_language = lang
            self._update_context_labels()
            self._add_log_message(f"Opened file: {file_name}", color="gray")

    def _update_context_labels(self): self.lang_label.setText(f"Language: {self.agent_core.active_language}"); self.script_label.setText(f"Script: {self.agent_core.current_script_name or 'None'}")
    def _add_log_message(self, message: str, color: str = "black", is_html: bool = False): # ... (as before)
        message_str = str(message) if message is not None else "";
        if is_html: self.log_area.append(message_str)
        else: escaped_message = message_str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'); self.log_area.append(f"<font color='{color}'>{escaped_message}</font>")
        self.log_area.ensureCursorVisible()
    def _update_code_view_area(self, script_path: str = None, script_content: str = None): # ... (as before)
        display_content = "";
        if script_path:
            try:
                with open(script_path, "r", encoding='utf-8') as f: display_content = f.read()
            except FileNotFoundError: display_content = f"// Error: Could not find script {script_path}"
            except Exception as e: display_content = f"// Error reading script {script_path}: {e}"
        elif script_content is not None: display_content = script_content
        else: display_content = "// No active script or script content to display."
        self.code_view_area.setPlainText(display_content)
        self.code_view_area.moveCursor(QtGui.QTextCursor.MoveOperation.Start)
    def on_send_command(self): # ... (as before)
        user_input = self.input_entry.text().strip()
        if not user_input: return
        self._add_log_message(f"> {user_input}", color="#555555")
        self.input_entry.clear(); self.input_entry.setFocus()
        results = self.agent_core.process_command(user_input)
        msg_color = "black"; status = results.get("status")
        if status == "error": msg_color = "red"
        elif status == "success": msg_color = "green"
        elif status == "clarification_needed": msg_color = "purple"
        if results.get("main_response"): self._add_log_message(results["main_response"], color=msg_color)
        if results.get("debug_info"): self._add_log_message(f"DEBUG: {results['debug_info']}", color="orange")
        if results.get("script_to_display_path"): self._update_code_view_area(script_path=results["script_to_display_path"])
        elif not results.get("current_script_name"): self._update_code_view_area(script_content="// No active script.")
        self.agent_core.active_language = results["active_language"]
        self.agent_core.current_script_name = results["current_script_name"]
        self._update_context_labels()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME_QSS)
    main_window = MyAppAgentPysideUI()
    main_window.show()
    sys.exit(app.exec())
