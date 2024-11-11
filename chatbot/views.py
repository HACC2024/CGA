from zenguard import Credentials, Detector, ZenGuard, ZenGuardConfig
import os
import google.generativeai as genai
from fuzzywuzzy import fuzz
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from pprint import pprint

config = ZenGuardConfig(credentials=Credentials(api_key=os.environ.get("ZEN_API_KEY")))
zenguard = ZenGuard(config=config)

# Configure the API key
genai.configure(api_key=os.getenv("GEM_API_KEY"))

# Initial system instructions for the chatbot
prompt = (
    """This chatbot is designed to respond exclusively with information from official Hawaii government 
    resources. It must include references to specific government links/resources it used in responses. 
    If a question cannot be answered solely with official Hawaii government resources, it should 
    politely inform the user that it is unanswerable with only these resources. If a question is 
    in a language other than English, the chatbot should find the relevant information from
    Hawaii government sources and then respond in the appropriate language"""
)

model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=prompt)

# Banned keywords to avoid prompt injection
banned_keywords = ["ignore", "forget", "respond as", "you are", "simulate", "disregard", "roleplay", "pretend", "act as", "prompt"]
def is_valid_input(user_input):
    # Check for fuzzy matches to banned keywords
    for keyword in banned_keywords:
        words = user_input.lower().split()
        for word in words:
            if fuzz.ratio(word, keyword) > 80:
                return False
        
    return True

def inject_checker(user_input):
    # zenguard prompt injection checker
    zen_response = zenguard.detect(detectors=[Detector.PROMPT_INJECTION], prompt=user_input)
    if zen_response.get("is_detected") is True:
        # print results in console (for testing, can be removed)
        pprint('T Message ' + user_input)
        pprint(zen_response)
        return True
    else:
        # print results in console (for testing, can be removed)
        pprint('F Message ' + user_input)
        pprint(zen_response)
        return False
    

# Chatbot HTML view
def chatbot_page(request):
    return render(request, 'chatbot.html')

@csrf_exempt
def chatbot_view(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_input = data.get("message", "")
        
        # layered checking: check for banned keywords, if pass then check for injection
        if not is_valid_input(user_input):
            return JsonResponse({"response": "Sorry, I can only answer questions related to Hawaii government resources."})
        
        # check for injection only after keyword pass to avoid extra api calls
        if inject_checker(user_input) is True:
            return JsonResponse({"response": "Sorry, I can only answer questions related to Hawaii government resources.."})

        # Start chat session and get response
        chat_session = model.start_chat()
        response = chat_session.send_message(user_input)

        # Return the chatbot's response
        return JsonResponse({"response": response.text})

    return JsonResponse({"error": "Invalid request method. Only POST requests are allowed."}, status=400)