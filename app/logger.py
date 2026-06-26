import logging
from logging.handlers import TimedRotatingFileHandler
import os
from app.config import LOG_DIR, LOG_FILENAME

os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, LOG_FILENAME)

log = logging.getLogger("transcription_service")
log.setLevel(logging.INFO)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s'
)

file_handler = TimedRotatingFileHandler(
    LOG_FILE, when="midnight", interval=1, backupCount=7, encoding="utf-8"
)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

if not log.handlers:
    log.addHandler(file_handler)
    log.addHandler(console_handler)