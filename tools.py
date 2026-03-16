#imports
import os 
from time import sleep
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import yagmail
import threading as th
import ollama as oll
import re
import shutil
import subprocess
import json
from text_parser import INTENT_KEYWORDS, DESTINATION_KEYWORDS, extract_and_parse_time




path_to_txt = "text files/"
path_to_context = "Ai context"

#Create databases to store todo list and context documents
list_engine = create_engine("sqlite:///Databases/data.db")
context_engine = create_engine("sqlite:///Databases/documents.db")
reminder_engine = create_engine("sqlite:///Databases/reminder.db")

Base = declarative_base()

#todolist structure class
class TodoList(Base):
    __tablename__ = "TodoList"
    id = Column(Integer, primary_key=True)
    tasks = Column(String)
    endtime = Column(String)
    starttime = Column(String)
    repeat = Column(String)

#documents structure class
class Documents(Base):
    __tablename__ = "Documents"
    id = Column(Integer, primary_key = True)
    title = Column(String)
    context = Column(String)

#rpeating reminder stucture class
class Reminder(Base):
    __tablename__ = "Reminders"
    id = Column(Integer, primary_key= True)
    task_id = Column(String)
    repeat_inc = Column(Integer)
    next_remind = Column(String)

Base.metadata.create_all(list_engine)
Base.metadata.create_all(context_engine)
Base.metadata.create_all(reminder_engine)

Session = sessionmaker(bind=list_engine)
list_session = Session()

doc_Session = sessionmaker(bind = context_engine)
doc_session = doc_Session()

reminder_Session = sessionmaker(bind = reminder_engine)
reminder_session = reminder_Session()

#class that holds all user input based functions for the assistant to use
class Tools:
    #constructor with variables to hold the different function keywords and a variable to store its previous response
    def __init__(self):
        self.keywords = {"todo": "You can add, remove, or list tasks in your todo list.",
                         "context": "You can add, delete, list or move context documents to the ai's context documents.",
                         "file": " You can save, open, date or delete text files from the ai directory or context folder.",
                         "ai": "You can ask the ai questions, it will use avaiable context and your todo list to answer needed questions.",
                         "web": " You can search things on wikipedia based of a keyword.",
                         "notification": "You can set reminders for specific dates or schedule repeating notifications for tasks, you can also delete them to stop any further notifications about a task.",

                         }
        self.ai_response = ""
        self.serverRun = False
        self.time_format = "%m/%d/%y %H:%M"
        self.time_format_seconds = self.time_format + ":%S"
    
    #function that returns teh functions keywords
    def getKeywords(self):
        return list(self.keywords)
    
    #function that returns the current time in the correct format
    def currenttime(self, dt_with_seconds = False):
        if dt_with_seconds:
            time = datetime.datetime.now().strftime(self.time_format_seconds)
            return datetime.datetime.strptime(time, self.time_format_seconds)
        return datetime.datetime.now().strftime(self.time_format)

    
    #function that checks the given time is in the correct format
    def timeCheck(self, time):
        if time is None:
            return False
        try:
            datetime.datetime.strptime(time, self.time_format)
            return True
        except ValueError:
            return False
    
    #function that gets the task id given the contents of the task
    def find_task_id(self, text):
        task = list_session.query(TodoList).filter(TodoList.tasks == text).first()
        if task == None:
            return None
        else:
            return task.id
    #function that gets the document id based off the a title
    def find_doc_id(self, text):
        doc = doc_session.query(Documents).filter(Documents.title == text).first()
        if doc == None:
            return None
        else:
            return doc.id

    #function that sends the email to my personal email as a reminder for a user inputed task
    def email(self, task):
        if task.endtime:
            response = f"Reminder to complete task '{task.tasks}' for {task.endtime}."
        else:
            response = f"Reminder to complete task '{task.tasks}', There is no end time set for task."

        yag = yagmail.SMTP("nlrwr24@gmail.com", "gozn nrvq wuyc aeio")
        yag.send(to="nicorelle351@gmail.com", subject = "Reminder", contents = response)

    
    #funtion that sets the time for the email to be sent and if not to sleep
    def remind(self, task, time):
        set_time = datetime.datetime.strptime(time, self.time_format)
        set_time = set_time.replace(second = 0)
        while True:
            ctime = self.currenttime(dt_with_seconds = True)
            try:
                dtime = set_time - ctime
                sleeptime = dtime.total_seconds()
                if ctime == set_time:
                    self.email(task)
                    self.delete_reminder(task.id)
                    break
                else:
                    sleep(sleeptime)
            except ValueError:
                return 
    
    #function that gets the context from the doc database to be sent to the ai based of keywords
    def get_context(self, question):
        words = self.get_keywords(question)
        for word in words:
            results = doc_session.query(Documents).filter(Documents.context.contains(word)).all()
            str_context = ""
            for doc in results:
                str_context += f"\n {doc.title}\n{'-'*40}\n{doc.context[:500]}...\n"
        return str_context if str_context else "No relevant context found."

    #function that gets the keywords from a query and returns the keywords in a list
    def get_keywords(self, question):
        stopwords = {
            'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'in', 'to', 'for', 'of', 'by', 'with', 'that', 'this', 'it', 'as', 'from'
        }
        # Remove punctuation and lowercase
        words = re.findall(r'\b\w+\b', question.lower())
        # Filter out stopwords
        keywords = [word for word in words if word not in stopwords]
        return keywords

    #funtion that saves data that is directly inputted into the assistant and saves it as the first word stated .txt
    def save_file(self, data):
        data = data.replace('. ', '.\n')
        first_space = data.find(" ")
        first_word = ""
        for i in range(first_space):
            first_word += data[i]
        first_word = path_to_txt + first_word + ".txt"
        with open(first_word, "x", encoding = "utf-8") as file:
            file.write(str(self.currenttime()) + "\n")
            file.write(data)
        return f"data saved to {first_word}"
    
    #function to remove a file from the text files folder or Ai context folder
    def remove_file(self, file_name):
        text_file_name = os.path.join(path_to_txt, file_name)
        if os.path.exists(text_file_name):
            try:
                os.remove(text_file_name)
                return f"File '{text_file_name}' removed from text files."
            except Exception as e:
                return f"Error removing file from text files: {e}"
        ai_context_path = os.path.join("Ai context", file_name)
        if os.path.exists(ai_context_path):
            try:
                os.remove(ai_context_path)
                return f"File '{file_name}' removed from Ai context folder."
            except Exception as e:
                return f"Error removing file from Ai context folder: {e}"
        return f"File '{file_name}' not found in current directory or Ai context folder."

    #function to move files back and forth between text files and Ai context 
    def move_file(self, title, folder_name = "context"):
        if folder_name == "file":
            doc_path = os.path.join(path_to_context, title)
            dst_folder = "text files"
            if not os.path.exists(dst_folder):
                os.makedirs(dst_folder)
            dst_path = os.path.join(dst_folder, os.path.basename(title))
            try:
                shutil.move(doc_path, dst_path)
                return f"File '{title}' moved to '{dst_folder}'."
            except Exception as e:
                return f"Error moving file: {e}"
        if folder_name == "context":
            doc_path = path_to_txt + title 
            dst_folder = "Ai context"
            if not os.path.exists(dst_folder):
                os.makedirs(dst_folder)
            dst_path = os.path.join(dst_folder, os.path.basename(title))
            try:
                shutil.move(doc_path, dst_path)
                return f"File '{title}' moved to '{dst_folder}'."
            except Exception as e:
                return f"Error moving file: {e}"
            
    #function that allows you to open files in the text files folder only
    def open_file(self, file_name):
        text_file_name = os.path.join(path_to_txt, file_name)
        if os.path.exists(text_file_name):
            try:
                if os.name == 'nt':  # Windows
                    abs_path = os.path.abspath(text_file_name)
                    if os.path.exists(abs_path):
                        os.startfile(abs_path)
                    else:
                        return f"File '{abs_path}' does not exist."
                elif os.name == 'posix':
                    # Try xdg-open (Linux), open (macOS), or fallback to nano
                    try:
                        subprocess.run(['xdg-open', file_name])
                    except FileNotFoundError:
                        try:
                            subprocess.run(['open', file_name])
                        except FileNotFoundError:
                            subprocess.run(['nano', file_name])
                return f"Opened '{file_name}' in the default text editor."
            except Exception as e:
                return f"Error opening file from text files: {e}"
        else:
            return "File you tried to open isn't located in text files folder. Ensure the file is moved into the text files folder."

    #a function that returns a list of all the files in the text files folder and then the Ai context folder
    def list_text_files(self):
        text_files = [f for f in os.listdir(path_to_txt) if f.endswith('.txt')]
        context_files = [f for f in os.listdir(path_to_context) if f.endswith('.txt')]
        file_list = ""
        if text_files:
            file_list += "\n\nText files:\n" + "\n".join(text_files)
        else:
            file_list += "text files:\nYou have no text files in this folder."
        if context_files:
            file_list += "\n\nContext files:\n" + "\n".join(context_files)
        else:
            file_list += "\n\nContext files:\nYou have no text files in this folder."
        return file_list

    #function to add the current time and date to a text file in the text files folder
    def add_date_to_file(self, file_name):
        file_path = os.path.abspath(os.path.join(path_to_txt, file_name))
        if not os.path.exists(file_path):
            return f"File '{file_name}' does not exist in text files. It must be in text files in order to edit."
        
        with open(file_path, "a", encoding="utf-8") as file:
            file.write("\n\n\n" + str(self.currenttime()) + "\n")
        return f"the Current time and date was added to '{file_name}'."

    #function that searches wikipedia based of a keyword that is given to it
    def search(self, query = ""):
        if query == "":
            return "No question asked"
        
        url = f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}"
        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            paragraphs = soup.find_all("p")
            
            
            non_empty_paragraphs = [para.text.strip() for para in paragraphs if para.text.strip()]
            if non_empty_paragraphs:
                return "\n\n".join(non_empty_paragraphs)
            
            return "No relevant content found."
        return "Page not accessible."

    #function that adds a task to the todo list database and then saves it
    def add(self, task, time=None):
        if not self.timeCheck(time):
            return f"Time format should be MM/DD/YY HH:MM"
        new_task = TodoList(tasks=task, endtime=time, starttime = datetime.datetime.now().strftime(self.time_format), repeat = "False")
        list_session.add(new_task)
        list_session.commit()
        return f"Task '{task}' added to the todo list. End time: {time if time else 'Not specified'}"
    
    #function that removes tasks from then database based of user inputted task_id
    def remove(self, task_id):
        task_to_delete = list_session.query(TodoList).filter(TodoList.id == task_id).first()
        if task_to_delete == None:
            return f"Task with Id {task_id} was not found in your todo list."
        else:
            list_session.delete(task_to_delete)
            list_session.commit()
            return f"Task with ID {task_id} removed from the todo list."

    #a funtion that returns a list of all the tasks saved in the todo list database
    def list_todo(self, show_start = False):
        if show_start == True:
            todo_list =  "\n".join([f"{task.id}: {task.tasks} (Start: {task.starttime}, End: {task.endtime})" for task in list_session.query(TodoList).all()])
        else:
            todo_list = "\n".join([f"{task.id}: {task.tasks} (Finish by: {task.endtime})" for task in list_session.query(TodoList).all()]) 
        if todo_list == "":
            return "Nothing"
            
        return todo_list

    #function thats sets the time for a reminder email to be sent and starts it on s eperate thread so that the user may still use the assistant 
    def remind_at(self, task_id, time, remind_inc = 0):
        task_obj = list_session.query(TodoList).filter(TodoList.id == task_id).first()
        if task_id == None or task_obj == None:
            return "Task not found"
        if time == "end time":
            time = task_obj.endtime
        if time is None or not self.timeCheck(time):
            return "Please specify a time for the reminder in the format MM/DD/YY HH:MM"
        if remind_inc == 0:
            reminder = th.Thread(target=self.remind, args= (task_obj, time))
            reminder.start()
        else:
            rep_remind = th.Thread(target = self.repeated_remind, args = (task_obj, time, remind_inc))
            rep_remind.start()
        new_reminder = Reminder(task_id = task_obj.id, repeat_inc = remind_inc, next_remind = time)
        reminder_session.add(new_reminder)
        reminder_session.commit()
        return f"Reminder for {task_obj.tasks} scheduled for {time}."

    #function that handle the notifications and adds the task to the reminder db to be able to manage them 
    def repeated_remind(self, task_obj, time, remind_inc):
        task_obj.repeat = "True"
        list_session.commit()
        reminder = th.Thread(target = self.remind, args = (task_obj, time))
        reminder.start()
        while True:
            reminder.join()
            repeated = reminder_session.query(Reminder).filter(Reminder.task_id == task_obj.id).first()
            if repeated:
                time = datetime.datetime.strptime(time, self.time_format_seconds)
                time = str(time + datetime.timedelta(days=remind_inc))
                reminder = th.Thread(target = self.remind, args = (task_obj, time))
                reminder.start()
                repeated.next_remind = time
                reminder_session.commit()
            else:
                break

    #function to list all repeating notifications
    def list_notifications(self):
        notifications = "notifications:\n"
        notifications += "\n".join([f"id: {reminder.id} task id: {reminder.task_id} next notification: {reminder.next_remind} reminder frequency: {reminder.repeat_inc}" for reminder in reminder_session.query(Reminder).all()])
        return notifications
    
    #function that deletes the notifications
    def delete_reminder(self, task_id):
        reminder = reminder_session.query(Reminder).filter(Reminder.task_id == task_id).first()
        if reminder:
            reminder_session.delete(reminder)
            reminder_session.commit()
            return f"Notification for reminder with id {task_id} was deleted."
        else:
            return f"Notifictiaction with task id: {task_id} not found. Please give valid id number."

    #funtion that sends context and the query to a local deepseek ai and generates a response based of the query(all data stays local)
    def ask_ai(self, query):
        context = self.get_context(query)
        if "todo list" in query:
            context += f"\ntodo list:\n{self.list_todo()}"
        print(context)
        Question = f"Question: {query}\n\nif this context isn't needed ignore it but here is some possible context that could help:\n\n{context}"
        question = oll.generate(model = "gemma3", prompt = Question)
        thought = question.response
        self.ai_response = f"\nAi responded:\n{thought}"
        if self.serverRun:
            yag = yagmail.SMTP("nlrwr24@gmail.com", "gozn nrvq wuyc aeio")
            yag.send(to="nicorelle351@gmail.com", subject = "Ai", contents = "Your ai response has been generated.")
            test = f"Ai-{self.currenttime().replace("/", "-")} \n{self.ai_response}"
            self.save_file(test)
        return self.ai_response

    #function that adds context to the documents database 
    def add_context(self, title):
        if not os.path.exists(f"Ai context/{title}"):
            return f"File {title} does not exist in Ai context folder."
        with open(f"Ai context/{title}", "r", encoding = "utf-8") as file:
            context = file.read()
        new_doc = Documents(title=title, context=context)
        doc_session.add(new_doc)
        doc_session.commit()
        return f"Context from {title} added to the Ai's knowledge base."
    
    #function to delete a specfifed document from the ai's context
    def delete_context(self, doc_id):
        doc_to_delete = doc_session.query(Documents).filter(Documents.id == doc_id).first()
        if doc_to_delete == None:
            return f"Document with ID {doc_id} was not found in context database."
        else:
            doc_session.delete(doc_to_delete)
            doc_session.commit()
            return f"Document with ID {doc_id} removed from the context database."

    #a function that deletes the entirety of the ai's user given context
    def clear_context(self):
        doc_session.query(Documents).delete()
        doc_session.commit()
        return "All context documents have been deleted from the database."
    
    #a function that returns a list of all the documents the ai has access too
    def list_ai_context(self):
        return "\n".join([f"{context.id} Document title: {context.title}" for context in doc_session.query(Documents).all()]) 

    #function that is called as a fallback if the text parser doesn't properly break up the input in a way that can execute tasks and return a dict same as the text_parser
    def fallback(self, message):
        question = f"Instruction: Given the following user input, extract the intent, task description, destination (if any), and time (if any). Return the result as a structured JSON object with no filler words for intent and destination. These are intent words: {INTENT_KEYWORDS}, These are destination words: {DESTINATION_KEYWORDS}"
        question += f"\nUser input:{message}'"
        question += "\nOutput format: {'intent': '...', 'task': '...', 'destination': '...', 'time': '...'}"
        thought = oll.generate(model = 'gemma3', prompt = question)
        response = thought.response
        dict = {}
        try:
            match = re.search(r"\{.*?\}", response, re.DOTALL)
            if match:
                json_str = match.group(0)
                dict = json.loads(json_str.replace("'", '"'))
            else:
                dict = eval(response)
        except Exception as e:
            dict = {"intent": "unknown", "task": "unknown", "destination": "unknown", "time": "unknown"}
        
        if dict['time'] != None:
            dict['time'] = extract_and_parse_time(dict['time'])
        print(dict)
        return dict
        
#testing main 
if __name__ == "__main__":
    tools = Tools()
    while True:
        message = input("Type message: ")
        print(tools.fallback(message))