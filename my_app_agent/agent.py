from conversational_engine import nlu, nlg

def main_loop():
    print(nlg.generate_response("greeting"))
    while True:
        user_input = input("> ")
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting agent. Goodbye!")
            break

        parsed_info = nlu.parse_intent(user_input)
        intent = parsed_info.get("intent")
        entities = parsed_info.get("entities")

        if intent == "unknown":
            response = nlg.generate_response("unknown_intent")
        elif intent == "create_script":
            # Placeholder for now - will eventually call code generator
            response = nlg.generate_response("confirmation") + " I'll create that script."
            print(f"DEBUG: Intent={intent}, Entities={entities}") # For our debugging
        elif intent == "add_function":
            # Placeholder
            response = nlg.generate_response("confirmation") + " I'll add that function."
            print(f"DEBUG: Intent={intent}, Entities={entities}") # For our debugging
        else:
            # Fallback for other intents we might add to NLU later
            response = nlg.generate_response("confirmation")

        print(response)

if __name__ == "__main__":
    main_loop()
