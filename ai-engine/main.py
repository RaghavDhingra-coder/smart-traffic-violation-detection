# TODO for ai-engine-application: add batching, model warmup, and production observability for inference workloads.
import base64

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from detector import ViolationDetector
from ocr import PlateOCR

app = FastAPI(title="Traffic Violation AI Engine", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # STUB: replace with real implementation using explicit trusted origins.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = ViolationDetector()
ocr = PlateOCR()


class RunRequest(BaseModel):
    image_base64: str
    source: str

    class Config:
        orm_mode = True


@app.get("/")
async def root():
    return {"message": "Traffic Violation AI Engine is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/run")
async def run_detection(payload: RunRequest):
    try:
        image_bytes = base64.b64decode(payload.image_base64)
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Failed to decode input image")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid image payload: {exc}") from exc

    try:
        detections = detector.detect(image)
        annotated_frame = detector.annotate_frame(image, detections)
        violations = []
        for detection in detections:
            plate_number = None
            plate_crop = detection.get("plate_crop")
            if plate_crop is not None:
                plate_number = ocr.extract_plate(plate_crop)
            violations.append(
                {
                    "type": detection["violation_type"],
                    "confidence": detection["confidence"],
                    "plate_number": plate_number,
                    "annotated_frame_base64": annotated_frame,
                }
            )
        return {"violations": violations}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc
