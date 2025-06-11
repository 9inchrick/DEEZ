from conversational_engine import nlu, nlg
from code_generator import python_generator, javascript_generator
import os

# display_script_content can remain as a utility for the CLI main_loop
def display_script_content_cli(script_path: str): # script_path is now absolute
    try:
        with open(script_path, "r") as f:
            content = f.read()
        print(f"--- Content of {os.path.basename(script_path)} (at {script_path}) ---") # Show basename and full path
        print(content)
        print("--- End of content ---")
    except FileNotFoundError:
        print(f"CLI: Error: Could not find script {script_path} to display.")
    except Exception as e:
        print(f"CLI: Error reading script {script_path}: {e}")


class AgentCore:
    def __init__(self):
        self.active_language = "python"
        self.current_script_name = None # Stores only the filename, e.g., "my_script.py"

    def process_command(self, user_input_str: str) -> dict:
        results = {
            "main_response": "", "debug_info": "", "script_to_display_path": None, # Will store absolute path
            "active_language": self.active_language, "current_script_name": self.current_script_name,
            "status": "success"
        }
        action_taken = False; debug_log = []
        parsed_info = nlu.parse_intent(user_input_str)
        intent = parsed_info.get("intent"); entities = parsed_info.get("entities", {})
        entities["current_language"] = self.active_language

        if intent == "unknown":
            results["main_response"] = nlg.generate_response("unknown_intent", entities); results["status"] = "error"
        elif intent == "specify_language":
            action_taken = True
            if "language" in entities:
                lang_to_set = entities["language"].lower()
                if lang_to_set in ["python", "javascript"]:
                    self.active_language = lang_to_set
                    results["main_response"] = nlg.generate_response(intent, entities)
                    self.current_script_name = None
                else:
                    results["main_response"] = f"Sorry, I don't fully support '{lang_to_set}'. Sticking with {self.active_language}."
                    results["status"] = "error"
            else:
                results["main_response"] = "Which language would you like to use?"
                results["status"] = "clarification_needed"

        elif intent == "create_script":
            action_taken = True
            script_filename = entities.get("script_name") # This is just the filename
            if not script_filename:
                results["main_response"] = nlg.ask_clarification("Name for the script?")
                results["status"] = "clarification_needed"
            else:
                try:
                    comment = f"Script '{script_filename}' auto-generated for {self.active_language} by MyAppAgent."
                    created_full_path = ""
                    if self.active_language == "python":
                        created_full_path = python_generator.create_new_script(script_filename, initial_comment=comment)
                        results["main_response"] = nlg.generate_response(intent, entities) + f" Python script created."
                    elif self.active_language == "javascript":
                        created_full_path = javascript_generator.create_new_js_script(script_filename, initial_comment=comment)
                        results["main_response"] = nlg.generate_response(intent, entities) + f" JavaScript script created."
                    else:
                        results["main_response"] = f"Language '{self.active_language}' does not support script creation."
                        results["status"] = "error"

                    if created_full_path and results["status"] == "success":
                        self.current_script_name = script_filename # Store just filename
                        results["script_to_display_path"] = created_full_path # Store full path
                except FileExistsError as fee:
                    results["main_response"] = str(fee)
                    results["status"] = "error"
                except Exception as e:
                    results["main_response"] = f"Error creating script: {type(e).__name__} - {e}"
                    results["status"] = "error"
                    debug_log.append(f"EXCEPTION in create_script: {type(e).__name__} - {e}")

        elif self.active_language == "python":
            action_taken = True
            target_script_filename = entities.get("target_script", self.current_script_name) # This is just filename
            target_script_explicitly_provided = "target_script" in entities

            # No script_path_to_modify here, generator returns it.

            if not target_script_filename and intent not in ["add_import_statement", "create_class_statement", "add_function"]: # Some ops might not need existing script
                 # For ops that modify existing scripts, target_script_filename is crucial
                 if intent not in ["create_script", "specify_language"]: # These don't strictly need a current script
                    results["main_response"] = nlg.ask_clarification("Which script are you working with or want to target?")
                    results["status"] = "clarification_needed"
                    action_taken = False # No further action if no target script for modification operations

            if action_taken and intent == "add_function":
                function_name = entities.get("function_name"); function_params = entities.get("parameters", [])
                if not function_name: results["main_response"] = nlg.ask_clarification("Function name?"); results["status"] = "clarification_needed"
                elif not target_script_filename: results["main_response"] = nlg.ask_clarification(f"Script for function '{function_name}'?"); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result_path = python_generator.add_function_to_script(target_script_filename, function_name, parameters=function_params)
                        if not gen_result_path.startswith("Error:"):
                            results["main_response"] = nlg.generate_response(intent, entities) + f" Func '{function_name}({', '.join(function_params)})' added to '{target_script_filename}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_filename
                            results["script_to_display_path"] = gen_result_path
                        else: results["main_response"] = gen_result_path; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding func: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in add_function: {type(e).__name__} - {e}")

            elif action_taken and intent == "add_method_to_class": # ... (similar updates for all python generator calls)
                class_name = entities.get("class_name"); method_name = entities.get("method_name"); parameters = entities.get("parameters", [])
                if not class_name or not method_name: results["main_response"] = nlg.ask_clarification("Missing class or method name."); results["status"] = "clarification_needed"
                elif not target_script_filename: results["main_response"] = nlg.ask_clarification(f"Script for class '{class_name}'?"); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result_path = python_generator.add_method_to_class(target_script_filename, class_name, method_name, parameters)
                        if not gen_result_path.startswith("Error:"):
                            results["main_response"] = nlg.generate_response(intent, entities) + f" Method '{method_name}({', '.join(parameters)})' added to class '{class_name}' in '{target_script_filename}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_filename
                            results["script_to_display_path"] = gen_result_path
                        else: results["main_response"] = gen_result_path; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding method: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in add_method: {type(e).__name__} - {e}")

            elif action_taken and intent == "add_class_attribute":
                class_name = entities.get("class_name"); attribute_name = entities.get("attribute_name"); value_expression = entities.get("value_expression")
                if not class_name or not attribute_name or value_expression is None: results["main_response"] = nlg.ask_clarification("Missing details for class attribute."); results["status"] = "clarification_needed"
                elif not target_script_filename: results["main_response"] = nlg.ask_clarification(f"Script for class '{class_name}'?"); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result_path = python_generator.add_class_attribute_to_class(target_script_filename, class_name, attribute_name, value_expression)
                        if not gen_result_path.startswith("Error:"):
                            results["main_response"] = nlg.generate_response(intent, entities) + f" Attribute {attribute_name} = {value_expression} added to class '{class_name}' in '{target_script_filename}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_filename
                            results["script_to_display_path"] = gen_result_path
                        else: results["main_response"] = gen_result_path; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding class attribute: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in add_class_attribute: {type(e).__name__} - {e}")

            elif action_taken and intent == "add_instance_attribute":
                class_name = entities.get("class_name"); attribute_name = entities.get("attribute_name"); value_expression = entities.get("value_expression"); init_param_suggestion = entities.get("init_param_suggestion")
                if not class_name or not attribute_name or value_expression is None: results["main_response"] = nlg.ask_clarification("Missing details for instance attribute."); results["status"] = "clarification_needed"
                elif not target_script_filename: results["main_response"] = nlg.ask_clarification(f"Script for class '{class_name}'?"); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result_path = python_generator.add_instance_attribute_to_init(script_name=target_script_filename, class_name=class_name, attribute_name=attribute_name, value_expression_str=value_expression, init_param_suggestion=init_param_suggestion)
                        if not gen_result_path.startswith("Error:"):
                            results["main_response"] = nlg.generate_response(intent, entities) + f" in class '{class_name}' in '{target_script_filename}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_filename
                            results["script_to_display_path"] = gen_result_path
                        else: results["main_response"] = gen_result_path; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding instance attribute: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in add_instance_attribute: {type(e).__name__} - {e}")

            elif action_taken and intent in ["add_print_statement", "add_return_statement", "add_conditional_statement", "add_for_loop", "add_while_loop", "add_file_operation", "add_try_except"]:
                item_name_from_nlu = entities.get("item_name", entities.get("function_name")); class_name_context = entities.get("class_name")
                item_type_for_generator = "method" if class_name_context else "function"
                item_name_for_generator = f"{class_name_context}.{item_name_from_nlu}" if item_type_for_generator == "method" else item_name_from_nlu
                if not item_name_from_nlu or not target_script_filename: results["main_response"] = nlg.ask_clarification(f"Missing func/method name or script for {intent}."); results["status"] = "clarification_needed"; valid_for_gen = False
                else: statement_kwargs = {}; statement_type_for_gen = ""; valid_for_gen = True # ... (validation logic as before) ...
                # (Full validation logic for each statement type as in previous version of agent.py)
                # For brevity, only showing the call and result handling
                if valid_for_gen: # Assuming validation passed
                    try:
                        gen_result_path = python_generator.add_statement_to_function_or_method(script_name=target_script_filename, item_name=item_name_for_generator, item_type=item_type_for_generator, statement_type=intent.replace("add_",""), **entities) # Pass relevant entities as kwargs
                        if not gen_result_path.startswith("Error:"):
                            results["main_response"] = nlg.generate_response(intent, entities) # NLG is context aware
                            if not target_script_explicitly_provided: self.current_script_name = target_script_filename
                            results["script_to_display_path"] = gen_result_path
                        else: results["main_response"] = gen_result_path; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding {intent}: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in {intent}: {type(e).__name__} - {e}")

            elif action_taken and intent == "add_import_statement":
                import_details = entities
                if not import_details.get("import_type") or not target_script_filename: results["main_response"] = nlg.ask_clarification("Missing import details or target script."); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result_path = python_generator.add_import_to_script(target_script_filename, import_details)
                        if not gen_result_path.startswith("Error:"):
                            if os.path.exists(gen_result_path): # Is a path
                                results["main_response"] = nlg.generate_response(intent, entities) + f" Import added to '{target_script_filename}'."
                                results["script_to_display_path"] = gen_result_path
                            else: # Is a success message like "already satisfied"
                                results["main_response"] = gen_result_path
                                # Still provide path for UI to show current state
                                results["script_to_display_path"] = os.path.join(python_generator.BASE_PYTHON_OUTPUT_DIR, target_script_filename)

                            if not target_script_explicitly_provided: self.current_script_name = target_script_filename
                        else: results["main_response"] = gen_result_path; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding import: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in add_import: {type(e).__name__} - {e}")

            elif action_taken and intent == "create_class_statement":
                class_name = entities.get("class_name")
                if not class_name: results["main_response"] = nlg.ask_clarification("Class name?"); results["status"] = "clarification_needed"
                elif not target_script_filename: results["main_response"] = nlg.ask_clarification(f"Script for class '{class_name}'?"); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result_path = python_generator.add_class_to_script(target_script_filename, class_name)
                        if not gen_result_path.startswith("Error:"):
                            results["main_response"] = nlg.generate_response(intent, entities) + f" Empty class '{class_name}' added to '{target_script_filename}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_filename
                            results["script_to_display_path"] = gen_result_path
                        else: results["main_response"] = gen_result_path; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error creating class: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in create_class: {type(e).__name__} - {e}")
            elif action_taken: # If it was a Python action but not any of the above
                action_taken = False # Reset because it's unhandled
                results["main_response"] = nlg.generate_response("unknown_intent", entities) + f" I can't do '{intent}' for Python code generation yet."
                results["status"] = "error"

            if action_taken: debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}'")

        elif self.active_language == "javascript": # ... (as before)
            if intent not in ["create_script", "specify_language"]:
                action_taken = True; results["main_response"] = f"Sorry, '{intent}' is not supported for JavaScript."; results["status"] = "error"
                debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}', Status='NotSupportedForJS'")
        else:  # ... (as before)
            if intent not in ["create_script", "specify_language"]: action_taken = True
            results["main_response"] = f"Advanced code generation for '{self.active_language}' is not supported."
            results["status"] = "error"
            if intent not in ["create_script", "specify_language"]: debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}', Status='LangNotSupported'")

        if intent in ["specify_language", "create_script"] and action_taken: # ... (debug logging as before)
            is_python_create_script = (self.active_language == "python" and intent == "create_script")
            logged_by_python_block = any("Intent='create_script'" in log_item and "Lang='python'" in log_item for log_item in debug_log if isinstance(log_item, str))
            if not (is_python_create_script and logged_by_python_block):
                 debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}'")

        if not results["main_response"] and action_taken and intent != "unknown": # ... (final fallbacks as before)
            results["main_response"] = nlg.generate_response("unknown_intent", entities) + f" Or I can't do '{intent}' with {self.active_language} yet."
            if results["status"] == "success": results["status"] = "error"
        elif not results["main_response"] and not action_taken and intent != "unknown":
             results["main_response"] = nlg.generate_response("unknown_intent", entities) + f" I can't do '{intent}' with {self.active_language} in the current state."
             if results["status"] == "success": results["status"] = "error"

        results["debug_info"] = " | ".join(debug_log)
        results["active_language"] = self.active_language
        results["current_script_name"] = self.current_script_name
        return results

def main_cli_loop(): # ... (as before)
    print("MyAppAgent CLI (Testing Mode)")
    agent_core = AgentCore()
    print(f"Agent ready. Language: {agent_core.active_language}, Script: {agent_core.current_script_name or 'None'}")
    while True:
        prompt_script_name = f" ({agent_core.current_script_name})" if agent_core.current_script_name else ""
        user_input = input(f"[{agent_core.active_language}{prompt_script_name}] CLI > ")
        if user_input.lower() in ["exit", "quit"]: print("Exiting agent CLI. Goodbye!"); break
        if not user_input.strip(): continue
        command_results = agent_core.process_command(user_input)
        if command_results.get("main_response"): print(f"Agent: {command_results['main_response']}")
        if command_results.get("debug_info"): print(f"DEBUG: {command_results['debug_info']}")
        if command_results.get("script_to_display_path"): display_script_content_cli(command_results["script_to_display_path"])

if __name__ == "__main__":
    main_cli_loop()
