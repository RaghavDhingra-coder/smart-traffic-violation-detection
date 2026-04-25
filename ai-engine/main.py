"""Phase 1 entry point: real-time webcam/video object detection using YOLOv8."""

from __future__ import annotations

import argparse
import base64
import logging
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from detector import YOLODetector
from ocr import crop_plate_from_vehicle, extract_text, is_plausible_plate, normalize_plate_text
from plate_detector import PlateDetector
from speed_estimator import estimate_speed
from tracker import ObjectTracker
from utils import draw_detections, draw_fps
from violations.helmet import detect_no_helmet
from violations.no_parking import detect_no_parking
from violations.signal import detect_signal_violation
from violations.triple_riding import detect_triple_riding

FRAME_SIZE = (416, 256)
API_FRAME_SIZE = (640, 384)
WINDOW_NAME = "Phase 2 - Object Detection + Tracking"
PLATE_DEBUG_WINDOW = "Plate Crop Debug"
OCR_MIN_BBOX_AREA = 12000
OCR_MIN_CONFIDENCE = 0.35
OCR_ALLOWED_CLASSES = {"car", "motorcycle"}
OCR_RETRY_INTERVAL_FRAMES = 18
OCR_MAX_TRACKS_PER_FRAME = 1
OCR_MAX_ATTEMPTS_PER_TRACK = 3
OCR_ENABLE_FULL_FRAME_FALLBACK = False
VEHICLE_LIKE_MIN_AREA = 30000
VEHICLE_LIKE_MIN_ASPECT = 1.20
OCR_CONFIRM_VOTES = 2
OCR_FULL_FRAME_VOTE_WEIGHT = 2
SIGNAL_STATE = "RED"  # can be RED or GREEN
STOP_LINE_Y = 170     # horizontal line across frame

# --------------------------------------------------------------------------- #
# Speed limits — expressed in pixels/second.                                   #
# Calibrate by logging raw speed values for a vehicle moving at a known speed. #
# A car moving at walking pace (~5 km/h) typically produces 40–80 px/s        #
# on a standard 416×256 inference frame.  Adjust to your scene.               #
# --------------------------------------------------------------------------- #
SPEED_LIMIT: float = 150.0      # px/s for local webcam / video file mode
API_SPEED_LIMIT: float = 80.0   # px/s for browser-streamed API frames

NO_PARKING_ZONE = (200, 200, 600, 500)  # (x1, y1, x2, y2)
API_TRACK_STALE_SECONDS = 2.5

app = FastAPI(title="Smart Traffic AI Engine", version="1.0.0")
logger = logging.getLogger("ai-engine")


class RunRequest(BaseModel):
    image_base64: str
    source: str = "webcam"


@dataclass(frozen=True)
class AnnotatedTrackedObject:
    """Tracked object with optional OCR plate text for rendering."""

    track_id: int
    class_id: int
    confidence: float
    bbox: tuple[int, int, int, int]
    plate: Optional[str] = None
    violation: Optional[str] = None


def crop_vehicle_from_frame(frame: np.ndarray, bbox: tuple[int, int, int, int]) -> Optional[np.ndarray]:
    """Safely crop a vehicle region from frame using tracked bbox."""
    if frame is None or frame.size == 0:
        return None

    frame_h, frame_w = frame.shape[:2]
    x1, y1, x2, y2 = bbox

    x1 = max(0, min(x1, frame_w - 1))
    y1 = max(0, min(y1, frame_h - 1))
    x2 = max(0, min(x2, frame_w - 1))
    y2 = max(0, min(y2, frame_h - 1))

    if x2 <= x1 or y2 <= y1:
        return None

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    return crop


def scale_bbox(
    bbox: tuple[int, int, int, int],
    src_size: tuple[int, int],
    dst_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    """
    Scale bbox from source size to destination size.

    src_size/dst_size are (width, height).
    """
    src_w, src_h = src_size
    dst_w, dst_h = dst_size
    x1, y1, x2, y2 = bbox

    if src_w <= 0 or src_h <= 0:
        return bbox

    sx = dst_w / float(src_w)
    sy = dst_h / float(src_h)

    return (
        int(x1 * sx),
        int(y1 * sy),
        int(x2 * sx),
        int(y2 * sy),
    )


def is_vehicle_like_bbox(bbox: tuple[int, int, int, int]) -> bool:
    """Heuristic fallback when detector class is noisy (e.g., car labeled as person)."""
    x1, y1, x2, y2 = bbox
    w = max(0, x2 - x1)
    h = max(1, y2 - y1)
    area = w * h
    aspect = w / float(h)
    return area >= VEHICLE_LIKE_MIN_AREA and aspect >= VEHICLE_LIKE_MIN_ASPECT


_detector: Optional[YOLODetector] = None
_tracker: Optional[ObjectTracker] = None
_plate_detector: Optional[PlateDetector] = None
_api_track_violation_cache: dict[int, set[str]] = {}
_api_track_last_seen: dict[int, float] = {}


def _get_runtime_components() -> tuple[YOLODetector, ObjectTracker, PlateDetector]:
    global _detector, _tracker, _plate_detector
    if _detector is None:
        # API mode needs lower confidence for small/far vehicles in browser streams.
        _detector = YOLODetector(model_path="yolov8n.pt", conf_threshold=0.25)
    if _tracker is None:
        # API receives sparse frames, so confirm tracks faster and retain them longer.
        _tracker = ObjectTracker(max_age=60, n_init=1, max_iou_distance=0.8)
    if _plate_detector is None:
        _plate_detector = PlateDetector()
    return _detector, _tracker, _plate_detector


def _decode_base64_image(image_base64: str) -> np.ndarray:
    encoded = image_base64.split(",")[-1].strip().replace("\n", "").replace("\r", "")
    if len(encoded) % 4:
        encoded += "=" * (4 - (len(encoded) % 4))
    try:
        image_bytes = base64.b64decode(encoded)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid base64 image payload") from exc

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Unable to decode image")
    return frame


def _extract_plate_from_crop(
    original_frame: np.ndarray,
    bbox: tuple[int, int, int, int],
    plate_detector: PlateDetector,
) -> Optional[str]:
    vehicle_crop = crop_vehicle_from_frame(original_frame, bbox)
    if vehicle_crop is None:
        return None

    plate_crop_yolo = plate_detector.detect_plate(vehicle_crop)
    plate_crop_fallback = crop_plate_from_vehicle(original_frame, bbox)
    for candidate in (plate_crop_yolo, plate_crop_fallback):
        if candidate is None or candidate.size == 0:
            continue
        text = extract_text(candidate)
        if text:
            plate = normalize_plate_text(text)
            if is_plausible_plate(plate):
                return plate
    return None


def run_single_frame_detection(image_base64: str, source: str = "webcam") -> dict:
    detector, tracker, plate_detector = _get_runtime_components()

    original_frame = _decode_base64_image(image_base64)
    orig_h, orig_w = original_frame.shape[:2]

    target_size = API_FRAME_SIZE if source == "webcam" else FRAME_SIZE
    frame = cv2.resize(original_frame, target_size)
    proc_h, proc_w = frame.shape[:2]
    effective_stop_line_y = max(0, min(STOP_LINE_Y, proc_h - 1))

    detections = detector.detect(frame)
    tracked_objects = tracker.update(detections, frame)

    # ------------------------------------------------------------------ #
    # FIX: compute active track ID set and pass it to estimate_speed so   #
    # stale entries are pruned and only current-frame speeds are returned. #
    # ------------------------------------------------------------------ #
    active_track_ids = {
        int(getattr(obj, "track_id", -1))
        for obj in tracked_objects
        if int(getattr(obj, "track_id", -1)) >= 0
    }
    speed_map = estimate_speed(tracked_objects, active_track_ids=active_track_ids)

    triple_v = detect_triple_riding(tracked_objects)
    helmet_v = detect_no_helmet(tracked_objects)
    signal_v = detect_signal_violation(tracked_objects, effective_stop_line_y, SIGNAL_STATE)
    no_parking_v = detect_no_parking(tracked_objects, NO_PARKING_ZONE)
    all_violations = triple_v + helmet_v + signal_v + no_parking_v

    overspeed_tracks = []
    speed_samples = []
    effective_speed_limit = API_SPEED_LIMIT if source == "webcam" else SPEED_LIMIT

    for obj in tracked_objects:
        track_id = int(getattr(obj, "track_id", -1))
        speed = speed_map.get(track_id)
        if speed is None:
            continue
        speed_samples.append({"track_id": track_id, "speed": round(float(speed), 2)})
        if speed > effective_speed_limit:
            all_violations.append({"track_id": track_id, "type": "OVERSPEEDING"})
            overspeed_tracks.append({"track_id": track_id, "speed": round(float(speed), 2)})

    max_speed = max((item["speed"] for item in speed_samples), default=0.0)
    logger.info(
        "ai_pipeline: source=%s raw_detections=%s tracked_objects=%s speed_limit=%.2f "
        "max_speed=%.2f speed_samples=%s violations_pre_ocr=%s overspeed_tracks=%s",
        source,
        len(detections),
        len(tracked_objects),
        effective_speed_limit,
        max_speed,
        speed_samples[:5],
        len(all_violations),
        overspeed_tracks[:5],
    )

    violation_by_track: dict[int, list[str]] = {}
    for violation in all_violations:
        track_id = int(violation.get("track_id", -1))
        vtype = str(violation.get("type", "")).strip().upper()
        if track_id < 0 or not vtype:
            continue
        violation_by_track.setdefault(track_id, [])
        if vtype not in violation_by_track[track_id]:
            violation_by_track[track_id].append(vtype)

    now = time.time()
    stale_track_ids = [
        track_id
        for track_id, last_seen in _api_track_last_seen.items()
        if (now - last_seen) > API_TRACK_STALE_SECONDS and track_id not in active_track_ids
    ]
    for track_id in stale_track_ids:
        _api_track_last_seen.pop(track_id, None)
        _api_track_violation_cache.pop(track_id, None)
    for track_id in active_track_ids:
        _api_track_last_seen[track_id] = now

    detections_payload = []
    tracks_with_violation = set(violation_by_track.keys())
    tracks_with_plate = set()

    for obj in tracked_objects:
        track_id = int(getattr(obj, "track_id", -1))
        if track_id not in violation_by_track:
            continue

        bbox = scale_bbox(obj.bbox, (proc_w, proc_h), (orig_w, orig_h))
        plate = _extract_plate_from_crop(original_frame, bbox, plate_detector)
        if plate:
            tracks_with_plate.add(track_id)
        else:
            plate = "UNKNOWN"

        for vtype in violation_by_track[track_id]:
            emitted_for_track = _api_track_violation_cache.setdefault(track_id, set())
            if vtype in emitted_for_track:
                continue
            emitted_for_track.add(vtype)
            detections_payload.append(
                {"track_id": track_id, "plate": plate, "type": vtype}
            )

    logger.info(
        "ai_pipeline: tracks_with_violation=%s tracks_with_plate=%s final_detections=%s",
        len(tracks_with_violation),
        len(tracks_with_plate),
        len(detections_payload),
    )

    return {"detections": detections_payload}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Real-time object detection with YOLOv8")
    parser.add_argument(
        "--source",
        default="0",
        help="Video source. Use 0 for webcam, or pass a video file path.",
    )
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="Path or name of YOLOv8 model (default: yolov8n.pt)",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.6,
        help="Confidence threshold for detections (default: 0.6)",
    )
    parser.add_argument(
        "--debug-plate",
        action="store_true",
        help="Show cropped plate images used for OCR.",
    )
    parser.add_argument(
        "--debug-ocr",
        action="store_true",
        help="Print OCR pipeline decisions for each track.",
    )
    parser.add_argument(
        "--debug-speed",
        action="store_true",
        help="Print raw px/s speed for every tracked vehicle each frame.",
    )
    parser.add_argument(
        "--disable-ocr",
        action="store_true",
        help="Disable plate detector + OCR for higher FPS.",
    )
    return parser.parse_args()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Smart Traffic AI engine is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run")
def run(request: RunRequest) -> dict:
    payload_chars = len(request.image_base64 or "")
    logger.info("ai_run: source=%s payload_b64_chars=%s", request.source, payload_chars)
    try:
        response = run_single_frame_detection(request.image_base64, source=request.source)
        detections = response.get("detections", [])
        logger.info(
            "ai_run: detections_count=%s detections_sample=%s",
            len(detections),
            detections[:2],
        )
        return response
    except HTTPException:
        logger.exception("ai_run: http_error")
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("AI engine /run failed")
        raise HTTPException(status_code=500, detail=f"AI engine failed: {exc}") from exc


def build_capture(source: str) -> cv2.VideoCapture:
    if source.isdigit():
        return cv2.VideoCapture(int(source))
    return cv2.VideoCapture(source)


def main() -> None:
    args = parse_args()
    capture = build_capture(args.source)

    if not capture.isOpened():
        print("Error: Unable to open camera/video source. Check webcam connection or source path.")
        capture.release()
        return

    try:
        detector = YOLODetector(model_path=args.model, conf_threshold=args.conf)
        tracker = ObjectTracker()
        plate_detector = None if args.disable_ocr else PlateDetector()
    except Exception as exc:  # noqa: BLE001
        print(f"Error: Failed to initialize detector/tracker: {exc}")
        capture.release()
        return

    prev_time = time.perf_counter()
    frame_count = 0

    # Cache successful OCR output per track.
    known_plates: dict[int, Optional[str]] = {}
    plate_votes: dict[int, dict[str, int]] = {}
    # Retry OCR periodically for tracks that previously failed.
    last_ocr_attempt_frame: dict[int, int] = {}
    ocr_attempt_count: dict[int, int] = {}
    # Stabilize noisy tracker metadata across frames.
    track_class_cache: dict[int, str] = {}
    track_conf_cache: dict[int, float] = {}
    debug_state_cache: dict[int, str] = {}
    total_signal_violations = 0

    try:
        while True:
            success, frame = capture.read()
            if not success:
                print("Info: End of stream or frame read failed. Exiting.")
                break

            original_frame = frame
            orig_h, orig_w = original_frame.shape[:2]

            frame = cv2.resize(frame, FRAME_SIZE)
            proc_h, proc_w = frame.shape[:2]
            effective_stop_line_y = max(0, min(STOP_LINE_Y, proc_h - 1))

            # Run detector/tracker on every second frame for performance.
            frame_count += 1
            if frame_count % 2 != 0:
                continue

            detections = detector.detect(frame)
            tracked_objects = tracker.update(detections, frame)

            # ---------------------------------------------------------------- #
            # FIX: build active ID set BEFORE calling estimate_speed so stale  #
            # tracks are pruned and only this frame's speeds are returned.      #
            # ---------------------------------------------------------------- #
            active_track_ids = {
                int(getattr(obj, "track_id", -1))
                for obj in tracked_objects
                if int(getattr(obj, "track_id", -1)) >= 0
            }
            speed_map = estimate_speed(tracked_objects, active_track_ids=active_track_ids)

            if args.debug_speed and speed_map:
                for tid, spd in speed_map.items():
                    print(f"[SPEED] track={tid} speed={spd:.1f} px/s  limit={SPEED_LIMIT}")

            # Phase 4: violation detection on tracked objects.
            triple_v = detect_triple_riding(tracked_objects)
            helmet_v = detect_no_helmet(tracked_objects)
            signal_v = detect_signal_violation(
                tracked_objects,
                effective_stop_line_y,
                SIGNAL_STATE,
            )
            no_parking_v = detect_no_parking(tracked_objects, NO_PARKING_ZONE)
            all_violations = triple_v + helmet_v + signal_v + no_parking_v

            for obj in tracked_objects:
                track_id = int(getattr(obj, "track_id", -1))
                # FIX: speed_map now returns only current-frame speeds, so
                # .get() correctly returns None for tracks with no fresh sample.
                speed = speed_map.get(track_id)
                if speed is None:
                    continue
                if speed > SPEED_LIMIT:
                    try:
                        object.__setattr__(obj, "violation", "OVERSPEEDING")
                    except Exception:  # noqa: BLE001
                        pass
                    all_violations.append({"track_id": track_id, "type": "OVERSPEEDING"})

            if signal_v:
                total_signal_violations += len(signal_v)
                print("Signal violations:", signal_v)

            for v in all_violations:
                for obj in tracked_objects:
                    if obj.track_id == v["track_id"]:
                        try:
                            object.__setattr__(obj, "violation", v["type"])
                        except Exception:  # noqa: BLE001
                            pass

            # track_id -> violation text, merge multiple violations.
            violation_map: dict[int, str] = {}
            for violation in all_violations:
                track_id = int(violation.get("track_id", -1))
                vtype = str(violation.get("type", "")).strip()
                if track_id < 0 or not vtype:
                    continue
                if track_id in violation_map:
                    existing = violation_map[track_id].split(", ")
                    if vtype not in existing:
                        violation_map[track_id] = f"{violation_map[track_id]}, {vtype}"
                else:
                    violation_map[track_id] = vtype

            # Precompute OCR-space bbox and largest track.
            bbox_for_ocr_map: dict[int, tuple[int, int, int, int]] = {}
            bbox_area_map: dict[int, int] = {}
            largest_track_id: Optional[int] = None
            largest_track_area = 0
            for tracked in tracked_objects:
                scaled_bbox = scale_bbox(tracked.bbox, (proc_w, proc_h), (orig_w, orig_h))
                area = (
                    max(0, scaled_bbox[2] - scaled_bbox[0])
                    * max(0, scaled_bbox[3] - scaled_bbox[1])
                )
                bbox_for_ocr_map[tracked.track_id] = scaled_bbox
                bbox_area_map[tracked.track_id] = area
                if area > largest_track_area:
                    largest_track_area = area
                    largest_track_id = tracked.track_id

            full_frame_plate_attempted = False
            full_frame_plate_text: Optional[str] = None
            full_frame_plate_crop: Optional[np.ndarray] = None

            prioritized_track_ids = sorted(
                bbox_area_map,
                key=lambda tid: bbox_area_map.get(tid, 0),
                reverse=True,
            )[:OCR_MAX_TRACKS_PER_FRAME]
            prioritized_track_set = set(prioritized_track_ids)

            annotated_objects: list[AnnotatedTrackedObject] = []
            for obj in tracked_objects:
                raw_class_name = detector.class_names.get(obj.class_id, str(obj.class_id))

                if raw_class_name in OCR_ALLOWED_CLASSES:
                    track_class_cache[obj.track_id] = raw_class_name
                class_name = track_class_cache.get(obj.track_id, raw_class_name)

                if obj.confidence > 0:
                    prev_best = track_conf_cache.get(obj.track_id, 0.0)
                    track_conf_cache[obj.track_id] = max(prev_best, obj.confidence)
                effective_conf = track_conf_cache.get(obj.track_id, obj.confidence)

                plate = known_plates.get(obj.track_id)

                last_attempt = last_ocr_attempt_frame.get(obj.track_id, -OCR_RETRY_INTERVAL_FRAMES)
                should_retry_now = (frame_count - last_attempt) >= OCR_RETRY_INTERVAL_FRAMES
                attempts_so_far = ocr_attempt_count.get(obj.track_id, 0)
                is_vehicle_candidate = class_name in OCR_ALLOWED_CLASSES or is_vehicle_like_bbox(obj.bbox)
                is_prioritized = obj.track_id in prioritized_track_set

                if (
                    not args.disable_ocr
                    and obj.track_id not in known_plates
                    and should_retry_now
                    and attempts_so_far < OCR_MAX_ATTEMPTS_PER_TRACK
                    and is_vehicle_candidate
                    and is_prioritized
                ):
                    last_ocr_attempt_frame[obj.track_id] = frame_count
                    ocr_attempt_count[obj.track_id] = attempts_so_far + 1
                    bbox_for_ocr = bbox_for_ocr_map.get(obj.track_id, obj.bbox)
                    x1, y1, x2, y2 = bbox_for_ocr
                    bbox_area = max(0, x2 - x1) * max(0, y2 - y1)
                    debug_reason = "skipped"

                    if effective_conf >= OCR_MIN_CONFIDENCE and bbox_area >= OCR_MIN_BBOX_AREA:
                        vehicle_crop = crop_vehicle_from_frame(original_frame, bbox_for_ocr)

                        plate_crop_yolo = (
                            plate_detector.detect_plate(vehicle_crop)
                            if (plate_detector is not None and vehicle_crop is not None)
                            else None
                        )
                        plate_crop_fallback = crop_plate_from_vehicle(original_frame, bbox_for_ocr)

                        candidates: list[tuple[str, Optional[np.ndarray]]] = [
                            ("yolo", plate_crop_yolo),
                            ("fallback", plate_crop_fallback),
                        ]
                        plate = None
                        used_source = "none"

                        for source_name, candidate in candidates:
                            if candidate is None or candidate.size == 0:
                                continue

                            if args.debug_plate:
                                debug_view = candidate.copy()
                                cv2.putText(
                                    debug_view,
                                    f"{source_name} {debug_view.shape[1]}x{debug_view.shape[0]}",
                                    (5, 18),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.5,
                                    (0, 255, 255),
                                    1,
                                    cv2.LINE_AA,
                                )
                                cv2.imshow(PLATE_DEBUG_WINDOW, debug_view)

                            plate = extract_text(candidate)
                            if plate:
                                used_source = source_name
                                break

                        if OCR_ENABLE_FULL_FRAME_FALLBACK and not plate and obj.track_id == largest_track_id:
                            if not full_frame_plate_attempted:
                                full_frame_plate_attempted = True
                                full_frame_plate_crop = (
                                    plate_detector.detect_plate(original_frame)
                                    if plate_detector is not None
                                    else None
                                )
                                full_frame_plate_text = (
                                    extract_text(full_frame_plate_crop)
                                    if full_frame_plate_crop is not None
                                    else None
                                )

                            if full_frame_plate_text:
                                plate = full_frame_plate_text
                                used_source = "full_frame"
                                if args.debug_plate and full_frame_plate_crop is not None and full_frame_plate_crop.size > 0:
                                    debug_full = full_frame_plate_crop.copy()
                                    cv2.putText(
                                        debug_full,
                                        f"full_frame {debug_full.shape[1]}x{debug_full.shape[0]}",
                                        (5, 18),
                                        cv2.FONT_HERSHEY_SIMPLEX,
                                        0.5,
                                        (0, 255, 0),
                                        1,
                                        cv2.LINE_AA,
                                    )
                                    cv2.imshow(PLATE_DEBUG_WINDOW, debug_full)

                        if plate:
                            plate = normalize_plate_text(plate)

                        if plate and is_plausible_plate(plate):
                            votes = plate_votes.setdefault(obj.track_id, {})
                            vote_increment = OCR_FULL_FRAME_VOTE_WEIGHT if used_source == "full_frame" else 1
                            votes[plate] = votes.get(plate, 0) + vote_increment
                            vote_count = votes[plate]
                            if vote_count >= OCR_CONFIRM_VOTES:
                                known_plates[obj.track_id] = plate
                                debug_reason = "ocr_ok"
                            else:
                                debug_reason = f"ocr_candidate({vote_count}/{OCR_CONFIRM_VOTES})"
                        else:
                            debug_reason = "ocr_empty"

                        if args.debug_ocr and not plate:
                            yolo_shape = None if plate_crop_yolo is None else plate_crop_yolo.shape[:2]
                            fb_shape = None if plate_crop_fallback is None else plate_crop_fallback.shape[:2]
                            print(
                                f"[OCRDBG] track={obj.track_id} yolo_shape={yolo_shape} "
                                f"fallback_shape={fb_shape} used={used_source}"
                            )
                        if args.debug_ocr and plate:
                            print(f"[OCRTXT] track={obj.track_id} source={used_source} text={plate}")
                    elif effective_conf < OCR_MIN_CONFIDENCE:
                        debug_reason = f"low_conf({effective_conf:.2f})"
                    elif bbox_area < OCR_MIN_BBOX_AREA:
                        debug_reason = f"small_bbox({bbox_area})"

                    if args.debug_ocr:
                        last_state = debug_state_cache.get(obj.track_id)
                        if last_state != debug_reason:
                            print(
                                f"[OCR] track={obj.track_id} class={class_name} "
                                f"conf={effective_conf:.2f} area={bbox_area} status={debug_reason}"
                            )
                            debug_state_cache[obj.track_id] = debug_reason

                annotated_objects.append(
                    AnnotatedTrackedObject(
                        track_id=obj.track_id,
                        class_id=obj.class_id,
                        confidence=obj.confidence,
                        bbox=obj.bbox,
                        plate=plate,
                        violation=violation_map.get(obj.track_id),
                    )
                )

            draw_detections(frame, annotated_objects, class_names=detector.class_names, min_confidence=0.5)
            cv2.rectangle(
                frame,
                (NO_PARKING_ZONE[0], NO_PARKING_ZONE[1]),
                (NO_PARKING_ZONE[2], NO_PARKING_ZONE[3]),
                (255, 0, 0),
                2,
            )
            cv2.putText(
                frame,
                "NO PARKING ZONE",
                (NO_PARKING_ZONE[0], max(20, NO_PARKING_ZONE[1] - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 0, 0),
                2,
                cv2.LINE_AA,
            )
            frame_width = frame.shape[1]
            cv2.line(frame, (0, effective_stop_line_y), (frame_width, effective_stop_line_y), (0, 0, 255), 2)
            cv2.putText(
                frame,
                f"Signal: {SIGNAL_STATE}  LineY: {effective_stop_line_y}",
                (10, 55),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255) if SIGNAL_STATE == "RED" else (0, 180, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                frame,
                f"Signal Violations: {total_signal_violations}",
                (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )

            current_time = time.perf_counter()
            fps = 1.0 / max(current_time - prev_time, 1e-6)
            prev_time = current_time
            draw_fps(frame, fps)

            cv2.imshow(WINDOW_NAME, frame)

            # ESC key to exit
            if cv2.waitKey(1) & 0xFF == 27:
                break
    except KeyboardInterrupt:
        print("Info: Interrupted by user. Exiting safely.")
    finally:
        capture.release()
        if args.debug_plate:
            try:
                cv2.destroyWindow(PLATE_DEBUG_WINDOW)
            except Exception:  # noqa: BLE001
                pass
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()