# Transcription Project

An asynchronous transcription microservice that uses FastAPI for its REST API, Celery for background job processing, Redis as a message broker, and the Deepgram API for generating transcriptions with speaker diarization.

## Features
- **FastAPI**: Provides high-performance RESTful API endpoints.
- **Celery & Redis**: Handles long-running transcription tasks asynchronously.
- **Deepgram Integration**: Uses Deepgram's `nova-3` model with multichannel and smart formatting enabled.
- **Role Classification**: Automatically identifies and groups conversations between an "agent" and a "customer" based on keyword heuristics.
- **Dockerized**: Easy setup using Docker and Docker Compose.

## Project Structure
```
.
├── app/
│   ├── services/
│   │   └── deepgram_service.py   # Handles Deepgram API requests
│   ├── utils/
│   │   ├── audio_chunker.py      # Utility to split large audio files
│   │   └── formatter.py          # Formats transcript results
│   ├── config.py                 # Loads environment variables
│   ├── logger.py                 # Configures application logging
│   ├── main.py                   # FastAPI application & endpoints
│   └── schemas.py                # Pydantic models for request validation
├── tasks/
│   └── transcription_task.py     # Celery tasks and transcript formatting logic
├── .env                          # Environment variables
├── celery_app.py                 # Celery instance configuration
├── docker-compose.yml            # Docker Compose configuration
├── Dockerfile                    # Docker build instructions
└── requirements.txt              # Python dependencies
```

## Environment Variables
Create a `.env` file in the root directory and configure the following variables:
```env
DEEPGRAM_API_KEY=your_deepgram_api_key_here
REDIS_URL=redis://redis:6379/0
LOG_DIR=./logs
LOG_FILENAME=app.log
```

## Running the Application

### Using Docker Compose (Recommended)
You can start both the FastAPI server and the Celery worker using Docker Compose:
```bash
docker-compose up --build -d
```
This will start the FastAPI application on `http://your-domain.com` (or `http://localhost:8023` locally).

### Running Locally (Without Docker)
1. Install dependencies:
```bash
pip install -r requirements.txt
```
2. Start the Redis server locally.
3. Start the FastAPI server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8023 --reload
```
4. Start the Celery worker:
```bash
celery -A celery_app.celery worker --loglevel=info --concurrency=2
```

## API Endpoints

### 1. Health Check
- **Endpoint:** `GET /`
- **Response:** `{"status": "running"}`

### 2. Submit Transcription Task
- **Endpoint:** `POST /api/v1/transcribe`
- **Required Header:** `X-API-Key: `

This single endpoint supports two different ways of submitting tasks:

**Option A: Using JSON (for URLs and Server File Paths)**
- **Header:** `Content-Type: application/json`
- **Header:** `X-API-Key: `
- **Body:**
```json
{
  "file_url": "https://example.com/audio.wav",
  "file_path": "/var/www/html/local_audio.wav"
}
```
*Note: Provide either `file_url` or `file_path`.*

**cURL Example (File URL):**
```bash
curl -X POST "http://your-domain.com/api/v1/transcribe" \
     -H "X-API-Key: " \
     -H "Content-Type: application/json" \
     -d '{"file_url": "https://example.com/audio.wav"}'
```

**cURL Example (File Path):**
```bash
curl -X POST "http://your-domain.com/api/v1/transcribe" \
     -H "X-API-Key: " \
     -H "Content-Type: application/json" \
     -d '{"file_path": "/var/www/html/local_audio.wav"}'
```

**Option B: Direct File Upload**
- **Header:** `Content-Type: multipart/form-data`
- **Header:** `X-API-Key: `
- **Body:** Send a form field named `file` containing your audio file.

**cURL Example (File Upload):**
```bash
curl -X POST "http://your-domain.com/api/v1/transcribe" \
     -H "X-API-Key: " \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/path/to/your/local/audio.wav"
```

- **Response:** Returns a `task_id` and a success message.

### 3. Check Task Status
- **Endpoint:** `GET /api/v1/status/{task_id}`
- **Required Header:** `X-API-Key: `
- **Response:** Returns the status of the transcription task (`PENDING`, `STARTED`, `SUCCESS`, or `FAILURE`). If successful, it will include the formatted transcript separating the agent and customer dialogues.
