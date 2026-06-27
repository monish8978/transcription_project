import os
import shutil
import uuid
import json
from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import TranscriptionRequest
from tasks.transcription_task import transcribe_task
from celery.result import AsyncResult
from celery_app import celery
from app.logger import log
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Transcription API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Security & CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://192.168.1.219", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("API_KEY", "VFItcm9vdEB0dnQjMTIz")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")
    return api_key
# -----------------------

UPLOAD_DIR = "/var/www/html/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = {".wav", ".mp3"}

@app.post("/api/v1/transcribe")
@limiter.limit("10/minute")
async def transcribe(request: Request, api_key: str = Depends(verify_api_key)):
    content_type = request.headers.get("content-type", "")
    
    file_url = None
    file_path = None
    saved_path = None

    if "application/json" in content_type:
        try:
            data = await request.json()
            file_url = data.get("file_url")
            file_path = data.get("file_path")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format")
    elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        file_url = form.get("file_url")
        file_path = form.get("file_path")
        file = form.get("file")
        
        if file and hasattr(file, "filename") and file.filename:
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(status_code=400, detail="Invalid file type. Only .wav and .mp3 are allowed.")
            
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            saved_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            file_size = 0
            with open(saved_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):  # Read in 1MB chunks
                    file_size += len(chunk)
                    if file_size > MAX_FILE_SIZE:
                        buffer.close()
                        os.remove(saved_path)
                        raise HTTPException(status_code=413, detail="File too large. Maximum size is 100MB.")
                    buffer.write(chunk)
                    
            file_path = saved_path
    else:
        raise HTTPException(status_code=415, detail="Unsupported Media Type. Use JSON or Form Data.")

    if not file_url and not file_path:
        raise HTTPException(status_code=400, detail="Provide file_url, file_path, or upload a file")

    log.info(f"Task received with file_url={file_url}, file_path={file_path}")
    task = transcribe_task.delay(file_url, file_path)

    response = {
        "task_id": task.id,
        "message": "Processing started"
    }
        
    return response

@app.get("/api/v1/status/{task_id}")
@limiter.limit("30/minute")
def status(request: Request, task_id: str, api_key: str = Depends(verify_api_key)):
    task = AsyncResult(task_id, app=celery)

    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None
    }


@app.get("/")
def health():
    return {"status": "running"}