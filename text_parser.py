#imports
import re
import parsedatetime
import datetime
from difflib import get_close_matches
from spellchecker import SpellChecker

#all keywords that are used to delegate tasks
INTENT_KEYWORDS = ["add", "save", "create", "delete", "remove", "remind", "clear", "list", "ask", "search", "move", "open", "date"]
DESTINATION_KEYWORDS = ["todo", "file", "context", "ai", "web", "notification", ]
global Repeating
Repeating = 0
#function to match words with they keywords with a 75% accuracy
def fuzzy_match(word, choices, cutoff=0.75):
    matches = get_close_matches(word, choices, n=1, cutoff=cutoff)
    return matches[0] if matches else False

#function to normalize any acronims and any spelling errors if possible
def normalize_input(text):
    replacements = {
        r"\bevery day\b": "every tomorrow",
        r"\btmrw\b": "tomorrow",
        r"\bmon\b": "monday",
        r"\btues\b": "tuesday",
        r"\bwed\b": "wednesday",
        r"\bthur\b": "thursday",
        r"\bfri\b": "friday",
        r"\bsat\b": "saturday",
        r"\bsun\b": "sunday",
        r"\btn\b": "tonight",
        r"\bone\b": "1",
        r"\btwo\b": "2",
        r"\bthree\b": "3",
        r"\bfour\b": "4",
        r"\bfive\b": "5",
        r"\bsix\b": "6",
        r"\bseven\b": "7",
        r"\beight\b": "8",
        r"\bnine\b": "9",
        r"\bten\b": "10",
        r"\beleven\b": "11",
        r"\btwelve\b": "12",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = re.sub(r"\bat (\d{1,2})(?![:\d]*\s*(am|pm))\b", r"at \1pm", text, flags=re.IGNORECASE)
    spell = SpellChecker()
    words = text.split()
    corrected = []
    run_intent = True
    run_destination = True
    
    for word in words:
        if re.match(r"^\d+$", word) or re.match(r"^\d{1,2}[:/]\d{1,2}([:/]\d{2,4})?$", word) or re.match(r"^\d{1,2}(am|pm)$", word, re.IGNORECASE) or re.match(r"^\d{1,2}$", word):
            corrected.append(word)
            continue
        fixed_intent = fuzzy_match(word, INTENT_KEYWORDS)
        fixed_destination = fuzzy_match(word, DESTINATION_KEYWORDS)
        if fixed_intent and run_intent:
            corrected.append(fixed_intent)
            run_intent = False
        elif fixed_destination and run_destination:
            corrected.append(fixed_destination)
            run_destination = False
        elif word == "todo":
            corrected.append(word)
        elif spell.known([word]):
            corrected.append(word)
        else:
            suggestion = spell.correction(word)
            corrected.append(suggestion if suggestion else word)

    text = " ".join(corrected)

    return text

cal = parsedatetime.Calendar()

#function that extracts the time phrase and is thne sent to parsedatetime to make a str dt object 
def extract_and_parse_time(text):
    match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4}(?:\s+\d{1,2}:\d{2})?)\b", text)
    if match:
        return match.group(1).strip()
        
    match = re.search(r"end time", text)
    if match:
        return match.group(0).strip()
    
    match = re.search(r"\bevery\s+(tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", text, re.IGNORECASE | re.VERBOSE)
    if match:
        phrase = match.group(0).strip()
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if any(word in phrase for word in days):
            global Repeating
            Repeating = 7
        else:
            Repeating = 1

    
    match = re.search(r"(tomorrow|tonight|today|next\s+\w+|this\s+\w+|monday|tuesday|wednesday|thursday|friday|saturday|sunday||in\s+\d+\s+\w+).*?(at\s+\d{1,2}(:\d{2})?\s*(am|pm)?|$)", text, re.IGNORECASE | re.VERBOSE)
    if not match:
        return "unknown"
    
    time_phrase = match.group(0).strip()

    time_struct, status = cal.parse(time_phrase)
    if status >= 1:
        dt = datetime.datetime(*time_struct[:6])
        return dt.strftime("%m/%d/%y %H:%M")

    return "unknown"

#function that extracts the destination keyword used 
def extract_destination(text):
    for word in text.split():
        match = fuzzy_match(word, DESTINATION_KEYWORDS)
        if match:
            return match
    return "unknown"

#function that extracts the intent keyword used
def extract_intent(text):
    for word in text.split():
        match = fuzzy_match(word, INTENT_KEYWORDS)
        if match:
            return match
    return "unknown"

#function that takes out the time phrase, intent keywords and fluff words and destination keywords and fluff words to get just what the task is meant to say 
def extract_task_only(text):
    question_match = re.search(r"(?:ask|tell|show)(?: me| ai)?(?:\s+)(.*)", text, flags=re.IGNORECASE)
    if question_match:
        return question_match.group(1).strip()

    time_pattern = r"(?:\b(for|at|on|by|in|every)\s+)?(?:every|today|tonight|tomorrow|next\s+\w+|this\s+\w+|monday|tuesday|wednesday|thursday|friday|saturday|sunday|in\s+\d+\s+(minutes?|hours?|days?)|at\s*\d{1,2}(?::\d{2})?\s*(am|pm)?|at\s*(am|pm)|end time)"
    text = re.sub(time_pattern, "", text, flags=re.IGNORECASE)

    text = re.sub(r"\b(for)\s+\d{1,2}/\d{1,2}/\d{2,4}(?:\s+\d{1,2}:\d{2})?\b(?:\s*)", "", text, flags=re.IGNORECASE)

    pattern = rf"(?:{'|'.join(INTENT_KEYWORDS)})(?: me)?(?: to| about| for)?\s+(.*)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return "Unknown"

    task = match.group(1).strip()

    destination_pattern = rf"(?:to|into|in|on|from|for|about|as)\s+(my |the |a )?(?:{'|'.join(DESTINATION_KEYWORDS)})s?( list)?"
    task = re.sub(destination_pattern, "", task, flags=re.IGNORECASE)

    task = re.sub(r"^the\s+", "", task, flags=re.IGNORECASE)
    trailing_dest = rf"(?:the\s+)?(?:{'|'.join(DESTINATION_KEYWORDS)})\s*$"
    task = re.sub(trailing_dest, "", task, flags=re.IGNORECASE)

    return task.strip()


#function that puts all previous together to return a diction ary containing all the extracted date from the inputted sentence
def parse_text(text):
    lowered = text.lower()
    intent = extract_intent(lowered)
    destination = extract_destination(lowered)
    lowered = normalize_input(lowered)
    task = extract_task_only(lowered)
    time = extract_and_parse_time(lowered)
    if Repeating > 0:
        return {
        "intent": intent,
        "task": task,
        "destination": destination,
        "time": time,
        "repeat": Repeating
    }

    else:
        return {
            "intent": intent,
            "task": task,
            "destination": destination,
            "time": time,
            "repeat": False
        }

#testing main
if __name__ == "__main__":
    while True:
        text = input(" ")
        important = parse_text(text)
        Repeating = 0
        print(important)