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

    def process_command(self, user_input_str: str) -> dict:
        results = {
            "main_response": "", "debug_info": "", "script_to_display_path": None,
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
            action_taken = True; script_name = entities.get("script_name")
            if not script_name:
                results["main_response"] = nlg.ask_clarification("Name for the script?")
                results["status"] = "clarification_needed"
            else:
                try:
                    comment = f"Script '{script_name}' auto-generated for {self.active_language} by MyAppAgent."
                    created_path = ""
                    if self.active_language == "python":
                        created_path = python_generator.create_new_script(script_name, initial_comment=comment)
                        results["main_response"] = nlg.generate_response(intent, entities) + " Python script created."
                    elif self.active_language == "javascript":
                        created_path = javascript_generator.create_new_js_script(script_name, initial_comment=comment)
                        results["main_response"] = nlg.generate_response(intent, entities) + " JavaScript script created."
                    else:
                        results["main_response"] = f"Language '{self.active_language}' not supported for script creation."
                        results["status"] = "error"

                    if created_path and results["status"] == "success":
                        self.current_script_name = script_name
                        results["script_to_display_path"] = created_path
                except FileExistsError as fee:
                    results["main_response"] = str(fee) + " Choose different name."
                    results["status"] = "error"
                except Exception as e:
                    results["main_response"] = f"Error creating script: {type(e).__name__} - {e}"
                    results["status"] = "error"
                    debug_log.append(f"EXCEPTION in create_script: {type(e).__name__} - {e}")

        # Python-specific block
        elif self.active_language == "python":
            action_taken = True
            target_script_for_op = entities.get("target_script", self.current_script_name)
            script_path_to_modify = os.path.join("generated_scripts", target_script_for_op) if target_script_for_op else None
            target_script_explicitly_provided = "target_script" in entities

            if intent == "add_function":
                function_name = entities.get("function_name"); function_params = entities.get("parameters", [])
                if not function_name:
                    results["main_response"] = nlg.ask_clarification("Function name?")
                    results["status"] = "clarification_needed"
                elif not target_script_for_op:
                    results["main_response"] = nlg.ask_clarification(f"Script for function '{function_name}'?")
                    results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result = python_generator.add_function_to_script(target_script_for_op, function_name, parameters=function_params)
                        if gen_result == "Success":
                            param_str = ", ".join(function_params)
                            results["main_response"] = nlg.generate_response(intent, entities) + f" Func '{function_name}({param_str})' added to '{target_script_for_op}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_for_op
                            results["script_to_display_path"] = script_path_to_modify
                        else: results["main_response"] = gen_result; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding func: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in add_function: {type(e).__name__} - {e}")

            elif intent == "add_method_to_class":
                class_name = entities.get("class_name"); method_name = entities.get("method_name"); parameters = entities.get("parameters", [])
                if not class_name or not method_name:
                    results["main_response"] = nlg.ask_clarification("Missing class or method name.")
                    results["status"] = "clarification_needed"
                elif not target_script_for_op:
                    results["main_response"] = nlg.ask_clarification(f"Script for class '{class_name}'?")
                    results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result = python_generator.add_method_to_class(target_script_for_op, class_name, method_name, parameters)
                        if gen_result == "Success":
                            params_str = ", ".join(parameters)
                            results["main_response"] = nlg.generate_response(intent, entities) + f" Method '{method_name}({params_str})' added to class '{class_name}' in '{target_script_for_op}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_for_op
                            results["script_to_display_path"] = script_path_to_modify
                        else: results["main_response"] = gen_result; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding method: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in add_method: {type(e).__name__} - {e}")

            elif intent == "add_class_attribute":
                class_name = entities.get("class_name"); attribute_name = entities.get("attribute_name")
                value_expression = entities.get("value_expression")
                if not class_name or not attribute_name or value_expression is None:
                    results["main_response"] = nlg.ask_clarification("Missing details for class attribute (class, attribute name, value, or script).")
                    results["status"] = "clarification_needed"
                elif not target_script_for_op:
                    results["main_response"] = nlg.ask_clarification(f"Script for class '{class_name}'?")
                    results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result = python_generator.add_class_attribute_to_class(
                            target_script_for_op, class_name, attribute_name, value_expression)
                        if gen_result == "Success":
                            results["main_response"] = nlg.generate_response(intent, entities) + \
                                f" Attribute {attribute_name} = {value_expression} added to class '{class_name}' in '{target_script_for_op}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_for_op
                            results["script_to_display_path"] = script_path_to_modify
                        else: results["main_response"] = gen_result; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding class attribute: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in add_class_attribute: {type(e).__name__} - {e}")

            elif intent == "add_instance_attribute":
                class_name = entities.get("class_name"); attribute_name = entities.get("attribute_name")
                value_expression = entities.get("value_expression"); init_param_suggestion = entities.get("init_param_suggestion")
                if not class_name or not attribute_name or value_expression is None:
                    results["main_response"] = nlg.ask_clarification("Missing class, attribute name, or value for instance attribute.")
                    results["status"] = "clarification_needed"
                elif not target_script_for_op:
                    results["main_response"] = nlg.ask_clarification(f"Script for class '{class_name}'?")
                    results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result = python_generator.add_instance_attribute_to_init(
                            script_name=target_script_for_op, class_name=class_name,
                            attribute_name=attribute_name, value_expression_str=value_expression,
                            init_param_suggestion=init_param_suggestion
                        )
                        if gen_result == "Success":
                            results["main_response"] = nlg.generate_response(intent, entities)
                            results["main_response"] += f" in class '{class_name}' in '{target_script_for_op}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_for_op
                            results["script_to_display_path"] = script_path_to_modify
                        else: results["main_response"] = gen_result; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding instance attribute: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in add_instance_attribute: {type(e).__name__} - {e}")

            elif intent in ["add_print_statement", "add_return_statement",
                            "add_conditional_statement", "add_for_loop", "add_while_loop",
                            "add_file_operation", "add_try_except"]: # Added add_try_except

                item_name_from_nlu = entities.get("item_name", entities.get("function_name"))
                class_name_context = entities.get("class_name")
                item_type_for_generator = "method" if class_name_context else "function"
                item_name_for_generator = f"{class_name_context}.{item_name_from_nlu}" if item_type_for_generator == "method" else item_name_from_nlu

                if not item_name_from_nlu or not target_script_for_op:
                    results["main_response"] = nlg.ask_clarification(f"Missing function/method name or target script for {intent}."); results["status"] = "clarification_needed"
                else:
                    statement_kwargs = {}; statement_type_for_gen = ""; valid_for_gen = True

                    if intent == "add_print_statement": statement_type_for_gen = "print"; statement_kwargs["expression_str"] = entities.get("expression")
                    elif intent == "add_return_statement": statement_type_for_gen = "return"; statement_kwargs["expression_str"] = entities.get("expression")
                    elif intent == "add_conditional_statement":
                        statement_type_for_gen = "conditional"
                        statement_kwargs["if_condition_str"] = entities.get("if_condition")
                        statement_kwargs["if_body_command_dict"] = entities.get("if_body_command")
                        statement_kwargs["else_body_command_dict"] = entities.get("else_body_command")
                    elif intent == "add_for_loop":
                        statement_type_for_gen = "for_loop"
                        statement_kwargs["loop_var_str"] = entities.get("loop_variable")
                        statement_kwargs["iterable_str"] = entities.get("iterable_expression")
                        statement_kwargs["body_command_dict"] = entities.get("body_command")
                    elif intent == "add_while_loop":
                        statement_type_for_gen = "while_loop"
                        statement_kwargs["condition_str"] = entities.get("condition_expression")
                        statement_kwargs["body_command_dict"] = entities.get("body_command")
                    elif intent == "add_file_operation":
                        statement_type_for_gen = "file_operation"
                        statement_kwargs["filename_str"] = entities.get("filename")
                        statement_kwargs["file_mode_str"] = entities.get("file_mode")
                        statement_kwargs["file_variable_name"] = entities.get("file_variable")
                        statement_kwargs["file_action_desc"] = entities.get("file_action")
                        if not all(statement_kwargs.values()): valid_for_gen = False # Basic check
                        elif statement_kwargs["file_action_desc"].get("type") == "unknown": valid_for_gen = False
                    elif intent == "add_try_except": # NEW
                        statement_type_for_gen = "try_except"
                        statement_kwargs["try_body_command_desc"] = entities.get("try_body_command_desc")
                        statement_kwargs["exception_type_str"] = entities.get("exception_type_str")
                        statement_kwargs["exception_as_variable"] = entities.get("exception_as_variable")
                        statement_kwargs["except_body_command_desc"] = entities.get("except_body_command_desc")
                        if not statement_kwargs["try_body_command_desc"] or \
                           statement_kwargs["try_body_command_desc"].get("type") == "unknown_statement" or \
                           not statement_kwargs["except_body_command_desc"] or \
                           statement_kwargs["except_body_command_desc"].get("type") == "unknown_statement":
                            results["main_response"] = nlg.ask_clarification("Missing details or unclear body commands for the try-except block.")
                            valid_for_gen = False

                    # Refined common validation checks
                    if valid_for_gen and "expression_str" in statement_kwargs and not statement_kwargs["expression_str"]:
                        results["main_response"] = nlg.ask_clarification(f"What to {statement_type_for_gen} in '{item_name_for_generator}'?"); valid_for_gen = False
                    if valid_for_gen and statement_type_for_gen == "conditional" and (not statement_kwargs.get("if_condition_str") or \
                       not statement_kwargs.get("if_body_command_dict") or statement_kwargs["if_body_command_dict"].get("type") == "unknown_statement" or \
                       (statement_kwargs.get("else_body_command_dict") and statement_kwargs["else_body_command_dict"].get("type") == "unknown_statement")):
                        results["main_response"] = nlg.ask_clarification("Missing details or unclear body for conditional."); valid_for_gen = False
                    if valid_for_gen and statement_type_for_gen == "for_loop" and (not statement_kwargs.get("loop_var_str") or not statement_kwargs.get("iterable_str") or \
                       not statement_kwargs.get("body_command_dict") or statement_kwargs["body_command_dict"].get("type") == "unknown_statement"):
                        results["main_response"] = nlg.ask_clarification("Missing details or unclear body for for-loop."); valid_for_gen = False
                    if valid_for_gen and statement_type_for_gen == "while_loop" and (not statement_kwargs.get("condition_str") or \
                       not statement_kwargs.get("body_command_dict") or statement_kwargs["body_command_dict"].get("type") == "unknown_statement"):
                        results["main_response"] = nlg.ask_clarification("Missing condition or unclear body for while-loop."); valid_for_gen = False

                    if not valid_for_gen: results["status"] = "clarification_needed"
                    else:
                        try:
                            gen_result = python_generator.add_statement_to_function_or_method(
                                script_name=target_script_for_op, item_name=item_name_for_generator,
                                item_type=item_type_for_generator,
                                statement_type=statement_type_for_gen, **statement_kwargs
                            )
                            if gen_result == "Success":
                                # Use specific NLG for try-except, generic for others here
                                if intent == "add_try_except":
                                    results["main_response"] = nlg.generate_response(intent, entities) + f" block added to '{item_name_for_generator}' in '{target_script_for_op}'."
                                else:
                                    results["main_response"] = nlg.generate_response(intent, entities) # NLG is context aware
                                if not target_script_explicitly_provided: self.current_script_name = target_script_for_op
                                results["script_to_display_path"] = script_path_to_modify
                            else: results["main_response"] = gen_result; results["status"] = "error"
                        except Exception as e: results["main_response"] = f"Error adding {statement_type_for_gen}: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in {intent}: {type(e).__name__} - {e}")

            elif intent == "add_import_statement":
                import_details = entities; import_type = import_details.get("import_type")
                is_direct_valid = import_type == "direct_import" and import_details.get("modules")
                is_from_valid = import_type == "from_import" and import_details.get("module") and import_details.get("names")
                if not import_type or not (is_direct_valid or is_from_valid) : results["main_response"] = nlg.ask_clarification("What module(s) or names to import, and how?"); results["status"] = "clarification_needed"
                elif not target_script_for_op: results["main_response"] = nlg.ask_clarification("Script for import?"); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result = python_generator.add_import_to_script(target_script_for_op, import_details)
                        if gen_result.startswith("Success"):
                            response_detail = gen_result; results["main_response"] = nlg.generate_response(intent, entities)
                            if response_detail == "Success": results["main_response"] += f" Import added to '{target_script_for_op}'."
                            else: results["main_response"] = response_detail
                            if not target_script_explicitly_provided: self.current_script_name = target_script_for_op
                            results["script_to_display_path"] = script_path_to_modify
                        else: results["main_response"] = gen_result; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding import: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in add_import: {type(e).__name__} - {e}")

            elif intent == "create_class_statement":
                class_name = entities.get("class_name")
                if not class_name: results["main_response"] = nlg.ask_clarification("Class name?"); results["status"] = "clarification_needed"
                elif not target_script_for_op: results["main_response"] = nlg.ask_clarification(f"Script for class '{class_name}'?"); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result = python_generator.add_class_to_script(target_script_for_op, class_name)
                        if gen_result == "Success":
                            results["main_response"] = nlg.generate_response(intent, entities) + f" Empty class '{class_name}' added to '{target_script_for_op}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_for_op
                            results["script_to_display_path"] = script_path_to_modify
                        else: results["main_response"] = gen_result; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error creating class: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION in create_class: {type(e).__name__} - {e}")
            else:
                action_taken = False
                results["main_response"] = nlg.generate_response("unknown_intent", entities) + f" I can't do '{intent}' for Python code generation yet."
                results["status"] = "error"

            if action_taken: debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}'")

        elif self.active_language == "javascript":
            if intent not in ["create_script", "specify_language"]:
                action_taken = True; results["main_response"] = f"Sorry, '{intent}' is not supported for JavaScript."; results["status"] = "error"
                debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}', Status='NotSupportedForJS'")
        else:
            if intent not in ["create_script", "specify_language"]: action_taken = True
            results["main_response"] = f"Advanced code generation for '{self.active_language}' is not supported."
            results["status"] = "error"
            if intent not in ["create_script", "specify_language"]: debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}', Status='LangNotSupported'")

        if intent in ["specify_language", "create_script"] and action_taken:
            is_python_create_script = (self.active_language == "python" and intent == "create_script")
            logged_by_python_block = any("Intent='create_script'" in log_item and "Lang='python'" in log_item for log_item in debug_log if isinstance(log_item, str))
            if not (is_python_create_script and logged_by_python_block):
                 debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}'")

        if not results["main_response"] and action_taken and intent != "unknown":
            results["main_response"] = nlg.generate_response("unknown_intent", entities) + f" Or I can't do '{intent}' with {self.active_language} yet."
            if results["status"] == "success": results["status"] = "error"
        elif not results["main_response"] and not action_taken and intent != "unknown":
             results["main_response"] = nlg.generate_response("unknown_intent", entities) + f" I can't do '{intent}' with {self.active_language} in the current state."
             if results["status"] == "success": results["status"] = "error"

        results["debug_info"] = " | ".join(debug_log)
        results["active_language"] = self.active_language
        results["current_script_name"] = self.current_script_name
        return results

def main_cli_loop():
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
