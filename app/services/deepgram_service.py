import httpx
import os
import asyncio
from fastapi import HTTPException
from app.config import DEEPGRAM_API_KEY
from app.logger import log

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


async def call_deepgram(headers, params, retries=3, **kwargs):
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    DEEPGRAM_URL,
                    headers=headers,
                    params=params,
                    **kwargs
                )

            # ✅ SUCCESS
            if response.status_code == 200:
                return response.json()   # 🔥 VERY IMPORTANT

            log.error(f"Deepgram error: {response.text}")

        except Exception:
            log.error(f"Retry {attempt+1} failed", exc_info=True)

        await asyncio.sleep(2)

    raise HTTPException(500, "Deepgram failed after retries")


async def process_audio(file_url=None, file_path=None):
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

    params = {
        "punctuate": "true",
        "diarize": "true",
        "model": "nova-3",
        "smart_format": "true",
        "utterances": "true",
        "language": "hi",
        "multichannel": "true"
    }

    # URL case
    if file_url:
        headers["Content-Type"] = "application/json"
        return await call_deepgram(headers, params, json={"url": file_url})

    # FILE case
    if file_path:
        if not os.path.exists(file_path):
            raise HTTPException(400, "File not found")

        headers["Content-Type"] = "audio/wav"

        with open(file_path, "rb") as f:
            audio_bytes = f.read()

        return await call_deepgram(headers, params, content=audio_bytes)

    raise HTTPException(400, "Provide file_url or file_path")