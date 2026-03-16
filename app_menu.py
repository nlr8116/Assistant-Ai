from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.metrics import dp
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.uix.widget import Widget
from Assistant import SimpleAI
from time import sleep
import keyboard as ky
import win32gui
import win32con


# Define the HomeScreen class, which is the main chat interface
class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize the SimpleAI assistant
        self.ai = SimpleAI()
        # Create the main vertical layout
        layout = BoxLayout(orientation='vertical')
        # Create the label to display conversation
        self.label = Label(
            text="\nAssistant: " + self.ai.greet(),
            size_hint_y=None,
            halign='left',
            valign='top',
            text_size=(0.95 * 800, None),
            color=(1, 1, 1, 1),
            font_size='16sp',
            padding=(dp(10), dp(10))
        )
        # Bind label height to its texture size for dynamic resizing
        self.label.bind(
            texture_size=lambda instance, value: setattr(self.label, 'height', value[1])
        )
        self.label.bind(width=lambda instance, value: setattr(self.label, 'text_size', (value, None)))
        # Create a scrollable view for the conversation
        self.scroll = ScrollView(size_hint=(1, 1), bar_width=dp(8), scroll_type=['bars', 'content'], do_scroll_x=False, bar_color=(0.95, 0.95, 0.98, 1))
        self.scroll.add_widget(self.label)
        # Create the input row for user text entry
        input_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), padding=[dp(8), dp(4)])
        self.textbox = TextInput(multiline=False, size_hint_x=1, height=dp(40), font_size='16sp', background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.1, 1), padding=[dp(10), dp(10)])
        self.textbox.bind(on_text_validate=self.on_enter)
        input_row.add_widget(self.textbox)
        # Add widgets to the main layout
        layout.add_widget(self.scroll)
        layout.add_widget(Widget(size_hint_y=None, height=dp(4)))
        layout.add_widget(input_row)
        self.add_widget(layout)
        # Refocus the textbox after pressing Enter
        def refocus_textbox(*args):
            Clock.schedule_once(lambda dt: setattr(self.textbox, 'focus', True), 0.1)
        self.textbox.bind(on_text_validate=lambda instance: (self.on_enter(instance), refocus_textbox()))

    # Handle user pressing Enter in the textbox
    def on_enter(self, instance = None):
        user_input = self.textbox.text
        if not user_input.strip():
            return
        # Check for exit commands
        if "exit now" in user_input.lower() or "quit now" in user_input.lower():
            self.label.text += f"\nYou: {user_input}\nAssistant: Goodbye"
            self.scroll.scroll_y = 0
            self.textbox.text = ""
            sleep(2)
            hwnd = win32gui.FindWindow(None, "Ai Assistant")
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            return
        # Get AI response and update the conversation
        airesponse = self.ai.respond(user_input)
        self.ai.lastmessage = airesponse
        self.label.text += f"\nYou: {user_input}\nAssistant: {airesponse}"
        self.label.text_size = (self.label.width, None)
        self.label.halign = 'left'
        self.label.valign = 'top'
        self.textbox.text = ""
        self.scroll.scroll_y = 0
        # Schedule periodic check for AI auto-responses
        self.checkai = Clock.schedule_interval(self.auto_respond, 10)

    # Periodically check for AI responses from background tasks
    def auto_respond(self, dt):
        if self.ai.ai_request and self.ai.tools.ai_response != '':
            airesponse = self.ai.tools.ai_response
            self.ai.lastmessage = airesponse
            self.label.text += f"\nAssistant: {airesponse}"
            self.label.text_size = (self.label.width, None)
            self.label.halign = 'left'
            self.label.valign = 'top'
            self.textbox.text = ""
            self.scroll.scroll_y = 0
            self.ai.ai_request = False
            self.checkai.cancel()
            self.ai.tools.ai_response = ''
    

# Define the AboutScreen class, which shows app information
class AboutScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=dp(20))
        # Info text about the Assistant.py class and usage
        info = """
Assistant.py is a Python class that provides a simple AI assistant with the following features:\n\n- Greets the user and responds to basic greetings.\n- Handles commands for saving, searching, managing to-do lists, reminders, and context documents.\n- Can interact with an AI model for advanced queries.\n- Supports multi-threaded AI requests and keyboard hotkeys.\n\nHow it works:\n1. Receives user input and parses commands.\n2. Delegates tasks to the Tools class for processing.\n3. Returns responses based on the command or query.\n\nExample Key words:  
    "todo": "You can add, remove, or list tasks in your todo list.",
    "context": "You can add, delete, list or move context documents to the ai's context documents.",
    "file": " You can save, open, date or delete text files from the ai directory or context folder.",
    "ai": "You can ask the ai questions, it will use avaiable context and your todo list to answer needed questions.",
    "web": " You can search things on wikipedia based of a keyword.",   """
        label = Label(text=info, halign='left', valign='top', font_size='16sp', color=(1,1,1,1), text_size=(0.95*800, None))
        label.bind(texture_size=lambda instance, value: setattr(label, 'height', value[1]))
        layout.add_widget(label)
        self.add_widget(layout)

# Define the MenuBar class for navigation between screens
class MenuBar(BoxLayout):
    def __init__(self, screen_manager, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=dp(48), **kwargs)
        self.screen_manager = screen_manager
        # Add Home and About buttons
        self.add_widget(Button(text='Home', on_release=self.switch_to_home))
        self.add_widget(Button(text='About', on_release=self.switch_to_about))

    # Switch to Home screen
    def switch_to_home(self, instance):
        self.screen_manager.current = 'home'

    # Switch to About screen
    def switch_to_about(self, instance):
        self.screen_manager.current = 'about'

# Define the main layout containing the menu and screens
class MainLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.screen_manager = ScreenManager()
        # Add Home and About screens to the manager
        self.screen_manager.add_widget(HomeScreen(name='home'))
        self.screen_manager.add_widget(AboutScreen(name='about'))
        # Add the menu bar and screen manager to the layout
        self.add_widget(MenuBar(self.screen_manager))
        self.add_widget(self.screen_manager)

# Define the main App class
class MyApp(App):
    def build(self):
        self.title = "Ai Assistant"
        return MainLayout()
    
    def on_start(self):
        try:
            ky.remove_hotkey('ctrl+alt+h')
        except Exception:
            pass
        def show_window():
            try:
                hwnd = win32gui.FindWindow(None, "Ai Assistant")
                if hwnd:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            except Exception as e:
                pass
        ky.add_hotkey("ctrl+alt+h", show_window)


# Run the app if this file is executed directly
if __name__ == '__main__':
    app_instance = MyApp()
    app_instance.run()
