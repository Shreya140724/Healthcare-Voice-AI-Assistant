from fastapi import FastAPI
from fastapi import UploadFile
from fastapi import File
from fastapi.middleware.cors import CORSMiddleware

import whisper
import edge_tts
import time

from fastapi.responses import FileResponse

from agent import process_user_message
from summary import generate_summary

# Create FastAPI app
app = FastAPI()

# ==========================================
# CORS
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Whisper Model
# ==========================================

whisper_model = whisper.load_model("base")

# ==========================================
# Root
# ==========================================

@app.get("/")
def root():

    return {
        "message": "Voice AI Agent Running"
    }

# ==========================================
# Chat Endpoint
# ==========================================

@app.post("/chat")
async def chat(data: dict):

    start = time.time()

    user_message = data.get("message")

    result = process_user_message(
        user_message
    )

    print(
        f"\nCHAT TIME: {time.time() - start:.2f} sec\n"
    )

    return result

# ==========================================
# Speech To Text
# ==========================================

@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...)
):

    audio_path = "temp_audio.wav"

    with open(audio_path, "wb") as f:
        f.write(await file.read())

    start = time.time()
    result = whisper_model.transcribe(
        audio_path,
        language="en",
        fp16=False,
        temperature=0
    )
    print(
    f"\nSTT TIME: {time.time() - start:.2f} sec\n"
)
    return {
        "text": result["text"]
    }

# ==========================================
# TTS
# ==========================================

@app.post("/tts")
async def tts(data: dict):

    start = time.time()

    text = data.get("text")

    audio_file = "response.mp3"

    communicate = edge_tts.Communicate(
        text=text,
        voice="en-IN-NeerjaNeural"
    )

    await communicate.save(audio_file)

    print(
        f"\nTTS TIME: {time.time() - start:.2f} sec\n"
    )

    return FileResponse(
        audio_file,
        media_type="audio/mpeg",
        filename="response.mp3"
    )
# ==========================================
# Summary Endpoint
# ==========================================

@app.post("/summary")
async def summary(data: dict):

    result = generate_summary(
        conversation_history=data.get(
            "conversation_history", []
        ),
        phone=data.get("phone")
    )

    return result
