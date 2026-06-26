import os
from dotenv import load_dotenv

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise Exception("DEEPGRAM_API_KEY not set")

LOG_DIR = os.getenv("LOG_DIR", "./logs")
LOG_FILENAME = os.getenv("LOG_FILENAME", "app.log")