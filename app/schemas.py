from pydantic import BaseModel

class TranscriptionRequest(BaseModel):
    file_url: str | None = None
    file_path: str | None = None