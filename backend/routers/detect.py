# TODO for detection-router: optimize video frame sampling, add background jobs, and improve failure reporting for long uploads.
import base64
import binascii
import imghdr
import tempfile
from pathlib import Path

import cv2
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from schemas.detection import DetectionResult, ViolationOut
from services.detection_service import (
    DetectionResponseError,
    DetectionServiceError,
    DetectionUpstreamError,
    run_detection,
    store_detected_violations,
)

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
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 frame payload") from exc

    suffix = ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(image_bytes)
        temp_path = temp_file.name

    try:
        violations = await run_detection(temp_path, source=payload.source)
        await store_detected_violations(violations, location=payload.source)
        return DetectionResult(violations=violations)
    except DetectionResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DetectionUpstreamError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DetectionServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except HTTPException:
        raise
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
            await store_detected_violations(violations, location="upload")
            processed = 1
        except DetectionResponseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except DetectionUpstreamError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except DetectionServiceError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
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
                    await store_detected_violations(frame_results, location="upload")
                    violations.extend(frame_results)
                    processed += 1
                finally:
                    Path(frame_path).unlink(missing_ok=True)
            frame_index += 1
        capture.release()
    except DetectionResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DetectionUpstreamError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DetectionServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except HTTPException:
        raise
    finally:
        Path(video_path).unlink(missing_ok=True)

    return DetectionResult(violations=violations, total_frames_processed=processed)
