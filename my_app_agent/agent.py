from conversational_engine import nlu, nlg
from code_generator import python_generator, javascript_generator
import os

# display_script_content can remain as a utility for the CLI main_loop
def display_script_content_cli(script_path: str):
    try:
        with open(script_path, "r") as f:
            content = f.read()
        print(f"--- Content of {script_path} ---")
        print(content)
        print("--- End of content ---")
    except FileNotFoundError:
        print(f"CLI: Error: Could not find script {script_path} to display.")
    except Exception as e:
        print(f"CLI: Error reading script {script_path}: {e}")


class AgentCore:
    def __init__(self):
        self.active_language = "python"
        self.current_script_name = None
        # self.loaded_scripts = {} # For future use

    def process_command(self, user_input_str: str) -> dict:
        results = {
            "main_response": "",
            "debug_info": "",
            "script_to_display_path": None,
            "active_language": self.active_language, # Will be updated before return
            "current_script_name": self.current_script_name, # Will be updated
            "status": "success" # Default status: "success", "error", "clarification_needed"
        }

        action_taken = False
        debug_log = []

        parsed_info = nlu.parse_intent(user_input_str)
        intent = parsed_info.get("intent")
        entities = parsed_info.get("entities", {})
        entities["current_language"] = self.active_language

        if intent == "unknown":
            results["main_response"] = nlg.generate_response("unknown_intent", entities)
            results["status"] = "error"
        elif intent == "specify_language":
            action_taken = True
            if "language" in entities:
                lang_to_set = entities["language"].lower()
                if lang_to_set in ["python", "javascript"]:
                    self.active_language = lang_to_set
                    results["main_response"] = nlg.generate_response(intent, entities)
                    self.current_script_name = None
                else:
                    results["main_response"] = f"Sorry, I don't fully support '{lang_to_set}' yet. Sticking with {self.active_language}."
                    results["status"] = "error" # Or keep current lang and succeed with a warning
            else:
                results["main_response"] = "Which language would you like to use?"
                results["status"] = "clarification_needed"
            debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}'")

        elif intent == "create_script":
            action_taken = True
            script_name = entities.get("script_name")
            if not script_name:
                results["main_response"] = nlg.ask_clarification("What do you want to name the script?")
                results["status"] = "clarification_needed"
            else:
                try:
                    comment = f"Script '{script_name}' auto-generated for {self.active_language} by MyAppAgent."
                    created_path = ""
                    if self.active_language == "python":
                        created_path = python_generator.create_new_script(script_name, initial_comment=comment)
                        results["main_response"] = nlg.generate_response(intent, entities) + f" Python script created."
                    elif self.active_language == "javascript":
                        created_path = javascript_generator.create_new_js_script(script_name, initial_comment=comment)
                        results["main_response"] = nlg.generate_response(intent, entities) + f" JavaScript script created."
                    else:
                        results["main_response"] = f"Language '{self.active_language}' does not support script creation."
                        results["status"] = "error"

                    if created_path: # If script creation was attempted and potentially succeeded
                        self.current_script_name = script_name # Update even if path is empty due to unsupported lang
                        if results["status"] == "success": # Only set path if successfully created
                             results["script_to_display_path"] = created_path
                        # main_response already set by specific language path
                except FileExistsError as fee:
                    results["main_response"] = str(fee) + " Choose a different name."
                    results["status"] = "error"
                except Exception as e:
                    results["main_response"] = f"Error creating script: {e}"
                    results["status"] = "error"
                    debug_log.append(f"EXCEPTION in create_script: {e}")
            debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}'")

        elif self.active_language == "python":
            action_taken = True # Assume action for Python block initially
            # All Python ops will target "generated_scripts/" + script_name
            target_script_for_op = entities.get("target_script", self.current_script_name)
            script_path_to_modify = None
            if target_script_for_op:
                 script_path_to_modify = os.path.join("generated_scripts", target_script_for_op)

            if intent == "add_function":
                function_name = entities.get("function_name"); function_params = entities.get("parameters", [])
                if not function_name:
                    results["main_response"] = nlg.ask_clarification("Function name?"); results["status"] = "clarification_needed"
                elif not target_script_for_op:
                    results["main_response"] = nlg.ask_clarification(f"Script for function '{function_name}'?"); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result = python_generator.add_function_to_script(target_script_for_op, function_name, parameters=function_params)
                        if gen_result == "Success":
                            param_str = ", ".join(function_params)
                            base_response = nlg.generate_response(intent, entities)
                            results["main_response"] = f"{base_response} Func '{function_name}({param_str})' added to '{target_script_for_op}'."
                            self.current_script_name = target_script_for_op; results["script_to_display_path"] = script_path_to_modify
                        else: results["main_response"] = gen_result; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding func: {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in add_function: {e}")

            elif intent in ["add_print_statement", "add_return_statement"]:
                function_name = entities.get("function_name"); expression_str = entities.get("expression")
                statement_type = "print" if intent == "add_print_statement" else "return"
                target_script_explicitly_provided = "target_script" in entities # Check before defaulting target_script_for_op
                if not function_name:
                    results["main_response"] = nlg.ask_clarification("Func to modify?"); results["status"] = "clarification_needed"
                elif not expression_str:
                    results["main_response"] = nlg.ask_clarification(f"What to {statement_type} in '{function_name}'?"); results["status"] = "clarification_needed"
                elif not target_script_for_op:
                    results["main_response"] = nlg.ask_clarification(f"Script for func '{function_name}'?"); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result = python_generator.add_statement_to_function(target_script_for_op, function_name, statement_type, expression_str)
                        if gen_result == "Success":
                            base_response = nlg.generate_response(intent, entities)
                            results["main_response"] = f"{base_response} Stmt '{statement_type} {expression_str}' added to func '{function_name}' in '{target_script_for_op}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_for_op
                            results["script_to_display_path"] = script_path_to_modify
                        else: results["main_response"] = gen_result; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding stmt: {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in add_statement: {e}")

            elif intent == "add_import_statement":
                import_details = entities
                import_type = import_details.get("import_type")
                is_direct_valid = import_type == "direct_import" and import_details.get("modules")
                is_from_valid = import_type == "from_import" and import_details.get("module") and import_details.get("names")

                if not import_type or not (is_direct_valid or is_from_valid) :
                    results["main_response"] = nlg.ask_clarification("What module(s) or names to import, and how?"); results["status"] = "clarification_needed"
                elif not target_script_for_op:
                    results["main_response"] = nlg.ask_clarification("Script for import?"); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result = python_generator.add_import_to_script(target_script_for_op, import_details)
                        if gen_result.startswith("Success"):
                            response_detail = gen_result
                            results["main_response"] = nlg.generate_response(intent, entities)
                            if response_detail == "Success": results["main_response"] += f" Import added to '{target_script_for_op}'."
                            else: results["main_response"] = response_detail
                            self.current_script_name = target_script_for_op; results["script_to_display_path"] = script_path_to_modify
                        else: results["main_response"] = gen_result; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding import: {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in add_import: {e}")

            elif intent == "create_class_statement":
                class_name = entities.get("class_name")
                if not class_name:
                    results["main_response"] = nlg.ask_clarification("Class name?"); results["status"] = "clarification_needed"
                elif not target_script_for_op:
                    results["main_response"] = nlg.ask_clarification(f"Script for class '{class_name}'?"); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result = python_generator.add_class_to_script(target_script_for_op, class_name)
                        if gen_result == "Success":
                            results["main_response"] = nlg.generate_response(intent, entities) + f" Empty class '{class_name}' added to '{target_script_for_op}'."
                            self.current_script_name = target_script_for_op; results["script_to_display_path"] = script_path_to_modify
                        else: results["main_response"] = gen_result; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error creating class: {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in create_class: {e}")
            else: # Unhandled Python intent
                action_taken = False # Not a recognized Python code-gen action
                results["main_response"] = nlg.generate_response("unknown_intent", entities) + f" I can't do '{intent}' for Python code generation yet."
                results["status"] = "error"

            if action_taken: debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}'")

        elif self.active_language == "javascript":
            if intent not in ["create_script", "specify_language"]: # create_script is handled globally
                action_taken = True # It's an action, just not supported for JS
                results["main_response"] = f"Sorry, the command '{intent}' is not yet supported for JavaScript beyond creating basic scripts."
                results["status"] = "error"
                debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}', Status='NotSupportedForJS'")
            # If it was create_script or specify_language, action_taken was set by their handlers.
            # No 'else: action_taken = False' here as it might override previous True from global handlers

        else: # Language other than Python or JS
            # Check if it was specify_language, which is always an action
            if intent != "specify_language":
                action_taken = True # Mark as action for unsupported lang
            results["main_response"] = f"Advanced code generation for '{self.active_language}' is not supported."
            results["status"] = "error"
            debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}', Status='LangNotSupported'")

        # Fallback if no specific response was set but an action was expected by a top-level handler
        if not results["main_response"] and action_taken and intent != "unknown":
            results["main_response"] = nlg.generate_response("unknown_intent", entities) + f" Or I can't do '{intent}' with {self.active_language} yet."
            if results["status"] == "success": results["status"] = "error" # Should be an error if it falls here
        elif not results["main_response"] and not action_taken and intent != "unknown":
            # An intent was parsed, but no handler took action (e.g. Python-only intent when lang is JS)
             results["main_response"] = nlg.generate_response("unknown_intent", entities) + f" I can't do '{intent}' with {self.active_language} in the current state."
             if results["status"] == "success": results["status"] = "error"


        results["debug_info"] = " | ".join(debug_log)
        results["active_language"] = self.active_language
        results["current_script_name"] = self.current_script_name

        return results


def main_cli_loop():
    """Simplified CLI loop for testing AgentCore."""
    print("MyAppAgent CLI (Testing Mode)")
    agent_core = AgentCore()
    # Initial greeting could be a specific method in AgentCore or handled by UI
    print(f"Agent ready. Language: {agent_core.active_language}, Script: {agent_core.current_script_name or 'None'}")

    while True:
        prompt_script_name = f" ({agent_core.current_script_name})" if agent_core.current_script_name else ""
        user_input = input(f"[{agent_core.active_language}{prompt_script_name}] CLI > ")

        if user_input.lower() in ["exit", "quit"]:
            print("Exiting agent CLI. Goodbye!")
            break

        if not user_input.strip():
            continue

        command_results = agent_core.process_command(user_input)

        if command_results.get("main_response"):
            print(f"Agent: {command_results['main_response']}")

        if command_results.get("debug_info"): # Only print if there's debug info
            print(f"DEBUG: {command_results['debug_info']}")

        if command_results.get("script_to_display_path"):
            display_script_content_cli(command_results["script_to_display_path"])

        # UI would use these to update its display
        # print(f"Status: {command_results['status']}")
        # print(f"Updated Lang: {command_results['active_language']}, Script: {command_results['current_script_name'] or 'None'}")


if __name__ == "__main__":
    main_cli_loop()
