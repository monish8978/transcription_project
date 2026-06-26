from pydub import AudioSegment
import os

CHUNK_MS = 60000

def split_audio(file_path):
    audio = AudioSegment.from_wav(file_path)
    chunks = []

    for i in range(0, len(audio), CHUNK_MS):
        chunk = audio[i:i + CHUNK_MS]
        path = f"{file_path}_chunk_{i}.wav"
        chunk.export(path, format="wav")
        chunks.append(path)

    return chunks