from fastapi import FastAPI
from app.schemas import TranscriptionRequest
from tasks.transcription_task import transcribe_task
from celery.result import AsyncResult
from celery_app import celery
from app.logger import log

app = FastAPI(title="Transcription API")


@app.post("/api/v1/transcribe")
async def transcribe(req: TranscriptionRequest):
    log.info("Request received")

    task = transcribe_task.delay(req.file_url, req.file_path)

    return {
        "task_id": task.id,
        "message": "Processing started"
    }

@app.get("/api/v1/status/{task_id}")
def status(task_id: str):
    task = AsyncResult(task_id, app=celery)

    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None
    }


@app.get("/")
def health():
    return {"status": "running"}