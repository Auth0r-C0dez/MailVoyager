# backend/conversation/utils.py
#this was used only during the base model creation
from dotenv import load_dotenv
import os

load_dotenv()  # Load variables from .env

def get_gmail_credentials():
    return {
        "email": os.getenv("GMAIL_USERNAME"),
        "password": os.getenv("GMAIL_PASSWORD")
    }
