from conversational_engine import nlu, nlg
# Updated import:
from code_generator import python_generator, javascript_generator
import os

# (display_script_content function remains the same)
def display_script_content(script_path: str):
    try:
        with open(script_path, "r") as f: content = f.read()
        print(f"--- Content of {script_path} ---"); print(content); print("--- End of content ---")
    except FileNotFoundError: print(f"Error: Could not find script {script_path} to display.")
    except Exception as e: print(f"Error reading script {script_path}: {e}")

def main_loop():
    print(nlg.generate_response("greeting")); active_language = "python"; current_script_name = None

    while True:
        prompt_script_name = f" ({current_script_name})" if current_script_name else ""
        user_input = input(f"[{active_language}{prompt_script_name}] > ")
        if user_input.lower() in ["exit", "quit"]: print("Exiting agent. Goodbye!"); break

        parsed_info = nlu.parse_intent(user_input)
        intent = parsed_info.get("intent"); entities = parsed_info.get("entities", {})
        entities["current_language"] = active_language # Pass current lang to NLG for context

        response = ""; action_taken = False

        if intent == "unknown": response = nlg.generate_response("unknown_intent", entities)
        elif intent == "specify_language":
            action_taken = True # This is an action handled by the agent.
            if "language" in entities:
                lang_to_set = entities["language"].lower()
                if lang_to_set in ["python", "javascript"]: # Supported languages
                    active_language = lang_to_set
                    response = nlg.generate_response(intent, entities)
                    current_script_name = None # Reset script context on language change
                else:
                    # Use NLG's generic response for specify_language if language is not directly supported for generation
                    # but still inform the user about limited support.
                    response = nlg.generate_response(intent, entities) + f" However, full support for '{lang_to_set}' is not yet available. Sticking to basic interactions."
                    # Optionally, revert to a default or keep the current if the language is truly unsupported.
                    # For now, we'll allow setting it but note limitations.
            else: response = "Which language would you like to use?"
            print(f"DEBUG: Intent='{intent}', Entities='{entities}', Current Language='{active_language}'")

        elif intent == "create_script":
            action_taken = True
            script_name = entities.get("script_name")
            if not script_name:
                response = nlg.ask_clarification("What do you want to name the script?")
            else:
                if active_language == "python":
                    try:
                        comment = f"Script '{script_name}' auto-generated for Python by MyAppAgent."
                        created_path = python_generator.create_new_script(script_name, initial_comment=comment)
                        # NLG now uses entities["current_language"]
                        response = nlg.generate_response(intent, entities) + f" Python script created at '{created_path}'."
                        current_script_name = script_name; display_script_content(created_path)
                    except FileExistsError as fee: response = str(fee) + " Choose a different name."
                    except Exception as e:
                        response = f"Error creating Python script: {e}"
                        print(f"DEBUG: Error creating Python script: {e}")
                elif active_language == "javascript":
                    try:
                        comment = f"Script '{script_name}' auto-generated for JavaScript by MyAppAgent."
                        created_path = javascript_generator.create_new_js_script(script_name, initial_comment=comment)
                        # NLG now uses entities["current_language"]
                        response = nlg.generate_response(intent, entities) + f" JavaScript script created at '{created_path}'."
                        current_script_name = script_name; display_script_content(created_path)
                    except FileExistsError as fee: response = str(fee) + " Choose a different name."
                    except Exception as e:
                        response = f"Error creating JavaScript script: {e}"
                        print(f"DEBUG: Error creating JS script: {e}")
                else:
                    response = f"Language '{active_language}' does not support script creation yet."
            print(f"DEBUG: Intent='{intent}', Entities='{entities}', Current Language='{active_language}'")

        elif active_language == "python":
            action_taken = True # Assume action is taken for any intent within this block
            # Python-specific actions
            if intent == "add_function":
                function_name = entities.get("function_name"); function_params = entities.get("parameters", [])
                target_script = entities.get("target_script", current_script_name)
                if not function_name: response = nlg.ask_clarification("Function name?")
                elif not target_script: response = nlg.ask_clarification(f"Script for function '{function_name}'?")
                else:
                    script_path_to_modify = os.path.join("generated_scripts", target_script)
                    try:
                        result = python_generator.add_function_to_script(target_script, function_name, parameters=function_params)
                        if result == "Success":
                            param_str = ", ".join(function_params)
                            base_response = nlg.generate_response(intent, entities)
                            response = f"{base_response} Function '{function_name}({param_str})' added to '{target_script}'."
                            current_script_name = target_script; display_script_content(script_path_to_modify)
                        else: response = result
                    except Exception as e:
                        response = f"Error adding function: {e}"
                        print(f"DEBUG: Error adding function: {e}")
            elif intent in ["add_print_statement", "add_return_statement"]:
                function_name = entities.get("function_name"); expression_str = entities.get("expression")
                target_script_explicitly_provided = "target_script" in entities
                target_script = entities.get("target_script", current_script_name)
                statement_type = "print" if intent == "add_print_statement" else "return"
                if not function_name: response = nlg.ask_clarification("Which function to modify?")
                elif not expression_str: response = nlg.ask_clarification(f"What to {statement_type} in '{function_name}'?")
                elif not target_script: response = nlg.ask_clarification(f"Script for function '{function_name}'?")
                else:
                    script_path_to_modify = os.path.join("generated_scripts", target_script)
                    try:
                        result = python_generator.add_statement_to_function(target_script, function_name, statement_type, expression_str)
                        if result == "Success":
                            base_response = nlg.generate_response(intent, entities)
                            response = f"{base_response} Statement '{statement_type} {expression_str}' added to func '{function_name}' in '{target_script}'."
                            if not target_script_explicitly_provided: current_script_name = target_script
                            display_script_content(script_path_to_modify)
                        else: response = result
                    except Exception as e:
                        response = f"Error adding statement: {e}"
                        print(f"DEBUG: Error adding statement: {e}")
            elif intent == "add_import_statement":
                import_details = entities; target_script = entities.get("target_script", current_script_name)
                import_type = import_details.get("import_type")
                is_direct_valid = import_type == "direct_import" and import_details.get("modules")
                is_from_valid = import_type == "from_import" and import_details.get("module") and import_details.get("names")
                if not import_type or not (is_direct_valid or is_from_valid):
                    response = nlg.ask_clarification("What module(s) or names to import, and how (e.g., 'import os' or 'from os import path')?")
                elif not target_script: response = nlg.ask_clarification("Script for import?")
                else:
                    script_path_to_modify = os.path.join("generated_scripts", target_script)
                    try:
                        result = python_generator.add_import_to_script(target_script, import_details)
                        if result.startswith("Success"):
                            response_detail = result
                            base_nlg_response = nlg.generate_response(intent, entities)
                            if response_detail == "Success": response = f"{base_nlg_response} Import added to '{target_script}'."
                            else: response = response_detail
                            current_script_name = target_script; display_script_content(script_path_to_modify)
                        else: response = result
                    except Exception as e:
                        response = f"Error adding import: {e}"
                        print(f"DEBUG: Error adding import: {e}")
            elif intent == "create_class_statement":
                class_name = entities.get("class_name"); target_script = entities.get("target_script", current_script_name)
                if not class_name: response = nlg.ask_clarification("Class name?")
                elif not target_script: response = nlg.ask_clarification(f"Script for class '{class_name}'?")
                else:
                    script_path_to_modify = os.path.join("generated_scripts", target_script)
                    try:
                        result = python_generator.add_class_to_script(target_script, class_name)
                        if result == "Success":
                            base_response = nlg.generate_response(intent, entities)
                            response = f"{base_response} Empty class '{class_name}' added to '{target_script}'."
                            current_script_name = target_script; display_script_content(script_path_to_modify)
                        else: response = result
                    except Exception as e:
                        response = f"Error creating class: {e}"
                        print(f"DEBUG: Error creating class: {e}")
            else: # Unhandled intent when language is Python
                action_taken = False # Not a recognized Python code-gen action
                response = nlg.generate_response("unknown_intent", entities) + f" I can't do '{intent}' for Python code generation yet."

            if action_taken and intent != "unknown": # If any python action was attempted
                 print(f"DEBUG: Intent='{intent}', Entities='{entities}', Current Language='{active_language}'")

        elif active_language == "javascript":
            # create_script is handled globally. Other JS actions are not supported yet.
            if intent not in ["create_script", "specify_language"]:
                action_taken = True # Mark as action attempted for JS
                response = f"Sorry, the command '{intent}' is not yet supported for JavaScript beyond creating basic scripts."
            # If it was specify_language or create_script, action_taken would have been set by their handlers.
            # No specific DEBUG print here unless a JS action was actually performed.
            # If create_script was the intent for JS, its specific DEBUG log would have printed.

        else: # Language other than Python or JS is selected
            action_taken = True # Consider it an action attempt, even if unsupported
            response = f"I'm currently set to '{active_language}'. Advanced code generation is not supported for this language yet."
            print(f"DEBUG: Intent='{intent}', Entities='{entities}', Current Language='{active_language}'")


        if response: print(response)
        elif not action_taken and intent != "unknown":
             # This case implies an intent was parsed, but no specific handler (Python, JS, global) took action.
             print(nlg.generate_response("unknown_intent", entities) + f" Or I can't do '{intent}' with {active_language} in the current state.")

if __name__ == "__main__":
    main_loop()
