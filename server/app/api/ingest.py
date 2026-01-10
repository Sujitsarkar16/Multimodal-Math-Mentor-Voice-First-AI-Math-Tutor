# app/api/ingest.py

from fastapi import APIRouter, UploadFile, File, Form
from app.multimodal.ocr import OCRService
from app.multimodal.asr import ASRService

router = APIRouter()


_ocr_service = None
_asr_service = None

def get_ocr_service():
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service

def get_asr_service():
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService()
    return _asr_service



@router.post("/ingest")
async def ingest(
    input_type: str = Form(...),  # text | image | audio
    text: str = Form(None),
    file: UploadFile = File(None),
):
    
    if input_type == "text":
        return {
            "raw_text": text,
            "confidence": 1.0,
            "needs_confirmation": False
        }
    
    import tempfile
    import os
    import shutil
    
    temp_dir = tempfile.gettempdir()

    if input_type == "image":
        if not file:
             return {"error": "File is required for image input"}
        
        image_path = os.path.join(temp_dir, file.filename)
        with open(image_path, "wb") as f:
            f.write(await file.read())

        return get_ocr_service().extract_text(image_path)

    if input_type == "audio":
        if not file:
             return {"error": "File is required for audio input"}

        audio_path = os.path.join(temp_dir, file.filename)
        with open(audio_path, "wb") as f:
            f.write(await file.read())

        return get_asr_service().transcribe(audio_path)

    return {"error": "Invalid input type"}
