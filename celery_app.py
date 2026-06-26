from celery import Celery
import os

celery = Celery(
    "tasks",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL")
)

celery.conf.update(
    result_backend=os.getenv("REDIS_URL"),
    task_track_started=True
)
# 🔥 important
celery.autodiscover_tasks(["tasks"])

# fallback safety
import tasks.transcription_task