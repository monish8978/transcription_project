import os
from dotenv import load_dotenv

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise Exception("DEEPGRAM_API_KEY not set")

LOG_DIR = os.getenv("LOG_DIR", "./logs")
LOG_FILENAME = os.getenv("LOG_FILENAME", "app.log")

DEEPGRAM_URL = os.getenv("DEEPGRAM_URL", "https://api.deepgram.com/v1/listen")
DEEPGRAM_PARAMS = {
    "punctuate": os.getenv("DEEPGRAM_PUNCTUATE", "true"),
    "diarize": os.getenv("DEEPGRAM_DIARIZE", "true"),
    "model": os.getenv("DEEPGRAM_MODEL", "nova-3"),
    "smart_format": os.getenv("DEEPGRAM_SMART_FORMAT", "true"),
    "utterances": os.getenv("DEEPGRAM_UTTERANCES", "true"),
    "language": os.getenv("DEEPGRAM_LANGUAGE", "hi"),
    "multichannel": os.getenv("DEEPGRAM_MULTICHANNEL", "true")
}