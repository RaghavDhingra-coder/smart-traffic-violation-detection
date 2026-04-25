import base64
import binascii
import imghdr
import logging
import tempfile
from pathlib import Path

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

try:
    from ..database import get_db
    from ..schemas.detection import DetectRequest, DetectResponse
    from ..services.challan_service import create_challan_from_detection
    from ..services.detection_service import (
        DetectionResponseError,
        DetectionServiceError,
        DetectionUpstreamError,
        run_detection,
    )
except ImportError:
    from database import get_db
    from schemas.detection import DetectRequest, DetectResponse
    from services.challan_service import create_challan_from_detection
    from services.detection_service import (
        DetectionResponseError,
        DetectionServiceError,
        DetectionUpstreamError,
        run_detection,
    )

router = APIRouter(prefix="/detect", tags=["detect"])
logger = logging.getLogger("backend.detect")


def _decode_base64_frame(frame: str) -> bytes:
    encoded = frame.split(",")[-1]
    try:
        return base64.b64decode(encoded)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 frame payload") from exc


@router.post("", response_model=DetectResponse)
async def detect_from_frame(payload: DetectRequest, db: Session = Depends(get_db)):
    _decode_base64_frame(payload.frame)
    encoded = payload.frame.split(",")[-1]
    logger.info(
        "detect_from_frame: source=%s payload_b64_chars=%s",
        payload.source,
        len(encoded),
    )

    try:
        detections = await run_detection(encoded, source=payload.source)
        logger.info(
            "detect_from_frame: detections_count=%s detections_sample=%s",
            len(detections),
            [item.dict() for item in detections[:2]],
        )
        stored_challans = []
        skipped_unknown_plate = 0
        for item in detections:
            if item.plate.strip().upper() == "UNKNOWN":
                skipped_unknown_plate += 1
                continue
            challan = await create_challan_from_detection(
                plate=item.plate,
                violation_type=item.type,
                db=db,
            )
            if challan:
                stored_challans.append(challan)
        logger.info(
            "detect_from_frame: stored_challans_count=%s skipped_unknown_plate=%s stored_challans_sample=%s",
            len(stored_challans),
            skipped_unknown_plate,
            [
                {
                    "id": c.id,
                    "plate": c.plate,
                    "violation_type": c.violation_type,
                    "status": c.status,
                }
                for c in stored_challans[:2]
            ],
        )
        return DetectResponse(detections=detections, stored_challans=stored_challans)
    except DetectionResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DetectionUpstreamError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DetectionServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/upload", response_model=DetectResponse)
async def detect_from_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    logger.info(
        "detect_from_upload: filename=%s bytes=%s",
        file.filename,
        len(file_bytes),
    )

    image_type = imghdr.what(None, h=file_bytes)
    encoded = None
    if image_type:
        encoded = base64.b64encode(file_bytes).decode("utf-8")
        logger.info("detect_from_upload: interpreted_as=image image_type=%s", image_type)
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix or ".mp4") as temp_video:
            temp_video.write(file_bytes)
            video_path = temp_video.name
        try:
            capture = cv2.VideoCapture(video_path)
            has_frame, frame = capture.read()
            capture.release()
            if not has_frame:
                raise HTTPException(status_code=400, detail="Unsupported upload: unable to read video frame")
            success, buffer = cv2.imencode(".jpg", frame)
            if not success:
                raise HTTPException(status_code=400, detail="Unsupported upload: failed to encode video frame")
            encoded = base64.b64encode(buffer.tobytes()).decode("utf-8")
            logger.info("detect_from_upload: interpreted_as=video extracted_first_frame=true")
        finally:
            Path(video_path).unlink(missing_ok=True)

    try:
        detections = await run_detection(encoded, source="upload")
        logger.info(
            "detect_from_upload: detections_count=%s detections_sample=%s",
            len(detections),
            [item.dict() for item in detections[:2]],
        )
        stored_challans = []
        skipped_unknown_plate = 0
        for item in detections:
            if item.plate.strip().upper() == "UNKNOWN":
                skipped_unknown_plate += 1
                continue
            challan = await create_challan_from_detection(
                plate=item.plate,
                violation_type=item.type,
                db=db,
            )
            if challan:
                stored_challans.append(challan)
        logger.info(
            "detect_from_upload: stored_challans_count=%s skipped_unknown_plate=%s stored_challans_sample=%s",
            len(stored_challans),
            skipped_unknown_plate,
            [
                {
                    "id": c.id,
                    "plate": c.plate,
                    "violation_type": c.violation_type,
                    "status": c.status,
                }
                for c in stored_challans[:2]
            ],
        )
        return DetectResponse(detections=detections, stored_challans=stored_challans)
    except DetectionResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DetectionUpstreamError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DetectionServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
