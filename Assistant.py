#imports
import random
from tools import Tools
import threading as th
import keyboard as key
from text_parser import parse_text, INTENT_KEYWORDS, DESTINATION_KEYWORDS



class SimpleAI(Tools):
    #constructor
    def __init__(self, name="AI"):
        self.name = name
        self.tools = Tools()
        self.lastmessage = ""
        self.ai_request = False

    #function to handle inital greeting
    def greet(self):
        greetings = [
            "Hello! How can I help you?",
            "Hi there! What can I do for you?",
            "Greetings! Need any assistance?"
        ]
        return random.choice(greetings)
    #main respond function that handles all the delegation of tasks and return approprate response
    def respond(self, message):
        if type(message) == type({}):
            project = message
            is_dict = True
        else:
            is_dict = False
            message = message.lower()
            message = message.replace("to do list", "todo list")
            message = message.replace("to-do", "todo")
        if "--help" in message:
            for word in self.tools.getKeywords():
                if word in message:
                    return f"{word}: {self.tools.keywords[word]}"
            return "Please specify a keyword for help. Available keywords: " + ", ".join(self.tools.getKeywords())
        elif any(word in message for word in DESTINATION_KEYWORDS) or any(word in message for word in INTENT_KEYWORDS) or is_dict:
            if not is_dict:
                project = parse_text(message)
            intent = project['intent']
            task = project['task']
            if "last assistant message" in task:
                task = task.replace("last assistant message", self.lastmessage)
            destination = project['destination']
            time = project['time']
            if destination == "notification":
                if intent == "delete":
                    return self.tools.delete_reminder(task if task.isdigit() else self.tools.find_task_id(task))
                if intent == "list":
                    return self.tools.list_notifications()
                if project['repeat']:
                    return self.tools.remind_at(task if task.isdigit() else self.tools.find_task_id(task), time, remind_inc= project['repeat'])
                else:
                    return self.tools.remind_at(task if task.isdigit() else self.tools.find_task_id(task), time)
            elif destination == "todo":
                if intent == "add":
                    return self.tools.add(task, time)
                elif intent == "delete" or intent == "remove":
                    task_id = self.tools.find_task_id(task) if not task.isdigit() else int(task)
                    if task_id == None:
                        return "Task was not found in your To-Do list."
                    return self.tools.remove(task_id)
                elif intent == "list":
                    return f"Your todo list:\n{self.tools.list_todo()}"
                else:
                    return "please specify what you are wanting to do with your todo list like 'add, delete, list'."
            elif destination == "file":
                if intent == "save":
                    return self.tools.save_file(task)
                elif intent == "remove" or intent == "delete":
                    return self.tools.remove_file(task)
                elif intent == "open":
                    return self.tools.open_file(task)
                elif intent == "move":
                    return self.tools.move_file(task, destination)
                elif intent == "list":
                    return self.tools.list_text_files()
                elif intent == "date":
                    return self.tools.add_date_to_file(task)
                else:
                    return "please specify what you are wanting to do with your file like 'save, delete, open'."
            elif destination == "context":
                if intent == "add":
                    return self.tools.add_context(task)
                elif intent == "delete" or intent == "remove":
                    context_id = self.tools.find_doc_id(task)
                    if context_id == None:
                        return "Context was not found in database."
                    return self.tools.delete_context(context_id)
                elif intent == "list":
                    return f"Ai's available context:\n{self.tools.list_ai_context()}"
                elif intent == "move":
                    return self.tools.move_file(task, destination)
                elif intent == "clear":
                    if task == "all":
                        return self.tools.clear_context()
                    else:
                        return "please write as 'clear all context' to ensure you want to clear all context documents."
                else:
                    return "please specify what you are wanting to do with your context documents like 'add, delete, list, move, clear'."
            elif destination == "ai":
                if intent == "ask":
                    th.Thread(target = self.tools.ask_ai, args = (task,)).start()
                    self.ai_request = True
                    return "Asking Ai, please wait, if you need help with something else in the meantime please ask."
                else:
                    return "A query is needed to ask AI."
                
            elif destination == "web":
                if intent == "search":
                    return "searched on wikipedia:\n" +self.tools.search(task)
                else:
                    return "please specify that you are wanting to search the web."
            else:
                if not is_dict:
                    return "Fallback used(Processing issues may occur):\n" + self.respond(self.tools.fallback(message))
                else:
                    return "I don't understand check your spelling or try re wording your request."

        elif "hello" in message or "hi" in message:
            return self.greet()
        elif "name" in message:
            return f"My name is {self.name}."
        elif "help" in message:
            return f"Here are some keywords I can assist with: {', '.join(self.tools.getKeywords())}.\nType a keyword followed by '--help' for more information."
        else:
            return "I'm not sure how to respond to that. check your spelling or try typing help."

if __name__ == "__main__":
    ai = SimpleAI("Assistant AI")
    print(ai.greet())
    while True:
        if ai.ai_request:
            if ai.tools.ai_response != "":
                print(ai.tools.ai_response)
                ai.lastmessage = ai.tools.ai_response
                ai.tools.ai_response = ""
                ai.ai_request = False
        user_input = input("You: ")
        if "exit now" in user_input.lower() or "quit now" in user_input.lower():
            if "sleep" in user_input.lower():
                print("Assistant: Going to sleep... (press esc to wake up)")
                key.wait(hotkey="esc")
                print(f"Assistant: Waking up...\n{ai.greet()}")
                continue
            print("Goodbye!")
            break
        airesponse = ai.respond(user_input)
        print("Assistant: " + airesponse)
        ai.lastmessage = str(airesponse)
        