from dotenv import load_dotenv
load_dotenv()

import os

API_KEYS = [
    key.strip()
    for key in os.getenv("GEMINI_API_KEYS", "").split(",")
    if key.strip()
]

MODEL = "gemini-2.5-flash"
