from conversational_engine import nlu, nlg
from code_generator import python_generator, javascript_generator 
import os

# display_script_content can remain as a utility for the CLI main_loop
def display_script_content_cli(script_path: str): # script_path is now absolute
    try:
        with open(script_path, "r", encoding='utf-8') as f: # Added encoding
            content = f.read()
        print(f"--- Content of {os.path.basename(script_path)} (at {script_path}) ---") 
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
            "main_response": "", "debug_info": "", "script_to_display_path": None, 
            "active_language": self.active_language, "current_script_name": self.current_script_name,
            "status": "success"
        }
        action_taken = False; debug_log = []
        parsed_info = nlu.parse_intent(user_input_str)
        intent = parsed_info.get("intent"); entities = parsed_info.get("entities", {})
        entities["current_language"] = self.active_language # For NLG context

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
            action_taken = True; script_filename = entities.get("script_name") 
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
                        results["main_response"] = f"Language '{self.active_language}' not supported for script creation."
                        results["status"] = "error"
                    
                    if created_full_path and results["status"] == "success": 
                        self.current_script_name = script_filename 
                        results["script_to_display_path"] = created_full_path 
                except FileExistsError as fee: 
                    results["main_response"] = str(fee) 
                    results["status"] = "error"
                except Exception as e: 
                    results["main_response"] = f"Error creating script: {type(e).__name__} - {e}"
                    results["status"] = "error"; debug_log.append(f"EXCEPTION in create_script: {type(e).__name__} - {e}")
        
        elif self.active_language == "python":
            action_taken = True
            target_script_filename = entities.get("target_script", self.current_script_name) 
            target_script_explicitly_provided = "target_script" in entities
            
            if not target_script_filename and intent not in ["add_import_statement", "create_class_statement", "add_function"]:
                 if intent not in ["create_script", "specify_language"]: 
                    results["main_response"] = nlg.ask_clarification("Which script are you working with or want to target?")
                    results["status"] = "clarification_needed"; action_taken = False 

            if action_taken and intent == "add_function": # ... (as before)
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
                    except Exception as e: results["main_response"] = f"Error adding func: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION: {type(e).__name__} - {e}")

            elif action_taken and intent == "add_method_to_class": # ... (as before)
                class_name = entities.get("class_name"); method_name = entities.get("method_name"); parameters = entities.get("parameters", [])
                body_command_descs = entities.get("body_command_descs", [{"type":"pass"}]) 
                if not class_name or not method_name: results["main_response"] = nlg.ask_clarification("Missing class or method name."); results["status"] = "clarification_needed"
                elif not target_script_filename: results["main_response"] = nlg.ask_clarification(f"Script for class '{class_name}'?"); results["status"] = "clarification_needed"
                elif any(cmd.get("type") == "unknown_statement" for cmd in body_command_descs):
                    results["main_response"] = nlg.ask_clarification(f"Method body contains unclear commands."); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result_path = python_generator.add_method_to_class(target_script_filename, class_name, method_name, parameters, body_command_descs)
                        if not gen_result_path.startswith("Error:"):
                            results["main_response"] = nlg.generate_response(intent, entities) + f" Method '{method_name}({', '.join(parameters)})' added to class '{class_name}' in '{target_script_filename}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_filename
                            results["script_to_display_path"] = gen_result_path
                        else: results["main_response"] = gen_result_path; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding method: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION: {type(e).__name__} - {e}")
            
            elif action_taken and intent == "add_decorator": # ... (as before)
                item_name_from_nlu = entities.get("item_name"); class_name_context = entities.get("class_name"); decorator_expression = entities.get("decorator_expression")
                item_type_for_generator = "method" if class_name_context else "function"
                if not item_name_from_nlu: results["main_response"] = nlg.ask_clarification("Which function or method to decorate?"); results["status"] = "clarification_needed"
                elif not target_script_filename: results["main_response"] = nlg.ask_clarification(f"Script for '{item_name_from_nlu}'?"); results["status"] = "clarification_needed"
                elif not decorator_expression: results["main_response"] = nlg.ask_clarification(f"What decorator for '{item_name_from_nlu}'?"); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result_path = python_generator.add_decorator_to_function_or_method(script_name=target_script_filename, item_name=item_name_from_nlu,item_type=item_type_for_generator, class_name_for_method=class_name_context, decorator_expression_str=decorator_expression)
                        if not gen_result_path.startswith("Error:"):
                            target_desc = f"method '{item_name_from_nlu}' in class '{class_name_context}'" if class_name_context else f"function '{item_name_from_nlu}'"
                            if gen_result_path.startswith("Success: Decorator already exists"): results["main_response"] = gen_result_path 
                            else: results["main_response"] = nlg.generate_response(intent, entities) + f" Decorator '@{decorator_expression}' added to {target_desc} in '{target_script_filename}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_filename
                            results["script_to_display_path"] = os.path.join(python_generator.BASE_PYTHON_OUTPUT_DIR, target_script_filename) if gen_result_path.startswith("Success:") else gen_result_path
                        else: results["main_response"] = gen_result_path; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding decorator: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION: {type(e).__name__} - {e}")

            elif action_taken and intent == "add_class_attribute":  # ... (as before)
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
                    except Exception as e: results["main_response"] = f"Error adding class attribute: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION: {type(e).__name__} - {e}")
            
            elif action_taken and intent == "add_instance_attribute": # ... (as before)
                class_name = entities.get("class_name"); attribute_name = entities.get("attribute_name"); value_expression = entities.get("value_expression"); init_param_suggestion = entities.get("init_param_suggestion_for_prop_attr", entities.get("init_param_suggestion")) # NLU key might vary based on context
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
                    except Exception as e: results["main_response"] = f"Error adding instance attribute: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION: {type(e).__name__} - {e}")
            
            elif action_taken and intent == "add_property_to_class": # NEW
                class_name = entities.get("class_name")
                property_name = entities.get("property_name")
                private_attr_name = entities.get("private_attribute_name") # NLU defaults this if not specified
                create_getter = entities.get("create_getter", True) # NLU should default this
                create_setter = entities.get("create_setter", False)
                create_deleter = entities.get("create_deleter", False)
                initial_value = entities.get("initial_value_for_init")
                init_param_sugg = entities.get("init_param_suggestion_for_prop_attr") # NLU specific key

                if not class_name or not property_name:
                    results["main_response"] = nlg.ask_clarification("Missing class or property name for adding property.")
                    results["status"] = "clarification_needed"
                elif not target_script_filename:
                    results["main_response"] = nlg.ask_clarification(f"Which script for class '{class_name}'?")
                    results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result_path = python_generator.add_property_to_class(
                            script_name=target_script_filename, class_name=class_name,
                            property_name=property_name, private_attr_name=private_attr_name,
                            create_getter=create_getter, create_setter=create_setter, create_deleter=create_deleter,
                            initial_value_for_init=initial_value, init_param_suggestion=init_param_sugg
                        )
                        if not gen_result_path.startswith("Error:"):
                            results["main_response"] = nlg.generate_response(intent, entities) # NLG is context aware
                            results["main_response"] += f" to class '{class_name}' in '{target_script_filename}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_filename
                            results["script_to_display_path"] = gen_result_path
                        else: results["main_response"] = gen_result_path; results["status"] = "error"
                    except Exception as e:
                        results["main_response"] = f"Error adding property: {type(e).__name__} - {e}"
                        results["status"] = "error"; debug_log.append(f"EXCEPTION in add_property: {type(e).__name__} - {e}")


            elif action_taken and intent in ["add_print_statement", "add_return_statement", "add_conditional_statement", 
                                             "add_for_loop", "add_while_loop", "add_file_operation", "add_try_except"]:
                # ... (This whole block for unified statement handling remains as before)
                item_name_from_nlu = entities.get("item_name", entities.get("function_name")); class_name_context = entities.get("class_name") 
                item_type_for_generator = "method" if class_name_context else "function"
                item_name_for_generator = f"{class_name_context}.{item_name_from_nlu}" if item_type_for_generator == "method" else item_name_from_nlu
                if not item_name_from_nlu or not target_script_filename: results["main_response"] = nlg.ask_clarification(f"Missing func/method name or script for {intent}."); results["status"] = "clarification_needed"; valid_for_gen = False
                else: statement_kwargs = {}; statement_type_for_gen = ""; valid_for_gen = True 
                    # ... (Populate statement_kwargs and statement_type_for_gen based on intent, and validation logic)
                    if intent == "add_print_statement": statement_type_for_gen = "print"; statement_kwargs["expression_str"] = entities.get("expression")
                    elif intent == "add_return_statement": statement_type_for_gen = "return"; statement_kwargs["expression_str"] = entities.get("expression")
                    elif intent == "add_conditional_statement": # ... (validation as before)
                        statement_type_for_gen = "conditional"; statement_kwargs["if_condition_str"] = entities.get("if_condition"); statement_kwargs["if_body_command_descs"] = entities.get("if_body_command_descs"); statement_kwargs["elif_clauses_descs"] = entities.get("elif_clauses"); statement_kwargs["else_body_command_descs"] = entities.get("else_body_command_descs")
                        if not statement_kwargs["if_condition_str"] or not statement_kwargs["if_body_command_descs"] or any(cmd.get("type") == "unknown_statement" for cmd in statement_kwargs["if_body_command_descs"]) or \
                           (statement_kwargs["elif_clauses_descs"] and any(not clause.get("condition") or not clause.get("body_command_descs") or any(cmd.get("type") == "unknown_statement" for cmd in clause.get("body_command_descs")) for clause in statement_kwargs["elif_clauses_descs"])) or \
                           (statement_kwargs["else_body_command_descs"] and any(cmd.get("type") == "unknown_statement" for cmd in statement_kwargs["else_body_command_descs"])): valid_for_gen = False; results["main_response"] = nlg.ask_clarification("Missing details or unclear body for conditional/elif/else.")
                    # ... (other statement types: for, while, file_op, try_except with their kwargs and validation)
                    
                    if not valid_for_gen: results["status"] = "clarification_needed"
                    else: # ... (call generator as before)
                        try:
                            gen_result_path = python_generator.add_statement_to_function_or_method(script_name=target_script_filename, item_name=item_name_for_generator, item_type=item_type_for_generator, statement_type=statement_type_for_gen, **statement_kwargs)
                            if not gen_result_path.startswith("Error:"): # ... (success handling)
                                results["main_response"] = nlg.generate_response(intent, entities)
                                if not target_script_explicitly_provided: self.current_script_name = target_script_filename
                                results["script_to_display_path"] = gen_result_path
                            else: results["main_response"] = gen_result_path; results["status"] = "error"
                        except Exception as e: results["main_response"] = f"Error adding {statement_type_for_gen}: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION: {type(e).__name__} - {e}")
            
            elif action_taken and intent == "add_import_statement": # ... (as before)
                import_details = entities; 
                if not import_details.get("import_type") or not target_script_filename: results["main_response"] = nlg.ask_clarification("Missing import details or target script."); results["status"] = "clarification_needed"
                else: # ... (call generator)
                    try:
                        gen_result_path = python_generator.add_import_to_script(target_script_filename, import_details)
                        if not gen_result_path.startswith("Error:"):  # ... (success handling)
                            if os.path.exists(gen_result_path): results["main_response"] = nlg.generate_response(intent, entities) + f" Import added to '{target_script_filename}'."; results["script_to_display_path"] = gen_result_path
                            else: results["main_response"] = gen_result_path ; results["script_to_display_path"] = os.path.join(python_generator.BASE_PYTHON_OUTPUT_DIR, target_script_filename) 
                            if not target_script_explicitly_provided: self.current_script_name = target_script_filename
                        else: results["main_response"] = gen_result_path; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error adding import: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION: {type(e).__name__} - {e}")
            
            elif action_taken and intent == "create_class_statement": # ... (as before, with base_classes)
                class_name = entities.get("class_name"); base_classes = entities.get("base_classes", [])
                if not class_name: results["main_response"] = nlg.ask_clarification("Class name?"); results["status"] = "clarification_needed"
                elif not target_script_filename: results["main_response"] = nlg.ask_clarification(f"Script for class '{class_name}'?"); results["status"] = "clarification_needed"
                else:
                    try:
                        gen_result_path = python_generator.add_class_to_script(target_script_filename, class_name, base_class_names=base_classes)
                        if not gen_result_path.startswith("Error:"):
                            results["main_response"] = nlg.generate_response(intent, entities) + f" in '{target_script_filename}'."
                            if not target_script_explicitly_provided: self.current_script_name = target_script_filename
                            results["script_to_display_path"] = gen_result_path
                        else: results["main_response"] = gen_result_path; results["status"] = "error"
                    except Exception as e: results["main_response"] = f"Error creating class: {type(e).__name__} - {e}"; results["status"] = "error"; debug_log.append(f"EXCEPTION: {type(e).__name__} - {e}")
            elif action_taken : 
                action_taken = False 
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

        if intent in ["specify_language", "create_script"] and action_taken: # ... (debug logging for global actions)
            is_python_create_script = (self.active_language == "python" and intent == "create_script")
            logged_by_python_block = any("Intent='create_script'" in log_item and "Lang='python'" in log_item for log_item in debug_log if isinstance(log_item, str))
            if not (is_python_create_script and logged_by_python_block):
                 debug_log.append(f"Intent='{intent}', Entities='{entities}', Lang='{self.active_language}'")

        if not results["main_response"] and action_taken and intent != "unknown": # ... (final fallbacks)
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
