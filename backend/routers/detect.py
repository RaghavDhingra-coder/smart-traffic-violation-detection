# TODO for detection-router: optimize video frame sampling, add background jobs, and improve failure reporting for long uploads.
import base64
import imghdr
import tempfile
from pathlib import Path

import cv2
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from schemas.detection import DetectionResult, ViolationOut
from services.detection_service import run_detection

router = APIRouter(prefix="/detect", tags=["detect"])


class DetectRequest(BaseModel):
    frame: str
    source: str = "webcam"

    class Config:
        orm_mode = True


@router.post("", response_model=DetectionResult)
async def detect_from_frame(payload: DetectRequest):
    try:
        encoded = payload.frame.split(",")[-1]
        image_bytes = base64.b64decode(encoded)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid base64 frame payload") from exc

    suffix = ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(image_bytes)
        temp_path = temp_file.name

    try:
        violations = await run_detection(temp_path, source=payload.source)
        return DetectionResult(violations=violations)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Detection failed: {exc}") from exc
    finally:
        Path(temp_path).unlink(missing_ok=True)


@router.post("/upload", response_model=DetectionResult)
async def detect_from_upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    image_type = imghdr.what(None, h=file_bytes)
    violations: list[ViolationOut] = []
    processed = 0

    if image_type:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{image_type}') as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name
        try:
            violations = await run_detection(temp_path, source="upload")
            processed = 1
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Image detection failed: {exc}") from exc
        finally:
            Path(temp_path).unlink(missing_ok=True)
        return DetectionResult(violations=violations, total_frames_processed=processed)

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix or '.mp4') as temp_video:
        temp_video.write(file_bytes)
        video_path = temp_video.name

    try:
        capture = cv2.VideoCapture(video_path)
        frame_index = 0
        while True:
            has_frame, frame = capture.read()
            if not has_frame:
                break
            if frame_index % 15 == 0:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as frame_file:
                    success, buffer = cv2.imencode('.jpg', frame)
                    if not success:
                        frame_index += 1
                        continue
                    frame_file.write(buffer.tobytes())
                    frame_path = frame_file.name
                try:
                    frame_results = await run_detection(frame_path, source="upload")
                    violations.extend(frame_results)
                    processed += 1
                finally:
                    Path(frame_path).unlink(missing_ok=True)
            frame_index += 1
        capture.release()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Video detection failed: {exc}") from exc
    finally:
        Path(video_path).unlink(missing_ok=True)

    return DetectionResult(violations=violations, total_frames_processed=processed)
