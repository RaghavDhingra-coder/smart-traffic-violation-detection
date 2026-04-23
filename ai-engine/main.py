"""Phase 1 entry point: real-time webcam/video object detection using YOLOv8."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from detector import YOLODetector
from ocr import crop_plate_from_vehicle, extract_text, is_plausible_plate, normalize_plate_text
from plate_detector import PlateDetector
from tracker import ObjectTracker
from utils import draw_detections, draw_fps

FRAME_SIZE = (416, 256)
WINDOW_NAME = "Phase 2 - Object Detection + Tracking"
PLATE_DEBUG_WINDOW = "Plate Crop Debug"
OCR_MIN_BBOX_AREA = 12000
OCR_MIN_CONFIDENCE = 0.35
OCR_ALLOWED_CLASSES = {"car", "motorcycle"}
OCR_RETRY_INTERVAL_FRAMES = 6
VEHICLE_LIKE_MIN_AREA = 30000
VEHICLE_LIKE_MIN_ASPECT = 1.20
OCR_CONFIRM_VOTES = 2
OCR_FULL_FRAME_VOTE_WEIGHT = 2


@dataclass(frozen=True)
class AnnotatedTrackedObject:
    """Tracked object with optional OCR plate text for rendering."""

    track_id: int
    class_id: int
    confidence: float
    bbox: tuple[int, int, int, int]
    plate: Optional[str] = None


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
    return parser.parse_args()


def build_capture(source: str) -> cv2.VideoCapture:
    # Keep default behavior exactly as requested: webcam source 0.
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
        plate_detector = PlateDetector()
    except Exception as exc:  # noqa: BLE001
        print(f"Error: Failed to initialize detector/tracker: {exc}")
        capture.release()
        return

    prev_time = time.perf_counter()
    frame_count = 0
    # Cache successful OCR output per track.
    known_plates: dict[int, Optional[str]] = {}
    plate_votes: dict[int, dict[str, int]] = {}
    # Retry OCR periodically for tracks that previously failed (avoids one-shot misses).
    last_ocr_attempt_frame: dict[int, int] = {}
    # Stabilize noisy tracker metadata across frames.
    track_class_cache: dict[int, str] = {}
    track_conf_cache: dict[int, float] = {}
    debug_state_cache: dict[int, str] = {}

    try:
        while True:
            success, frame = capture.read()
            if not success:
                print("Info: End of stream or frame read failed. Exiting.")
                break

            original_frame = frame
            orig_h, orig_w = original_frame.shape[:2]

            # Optimization 1: smaller frame for faster inference.
            frame = cv2.resize(frame, FRAME_SIZE)
            proc_h, proc_w = frame.shape[:2]

            # Optimization 2: run detector/tracker on every second frame.
            frame_count += 1
            if frame_count % 2 != 0:
                continue

            detections = detector.detect(frame)
            tracked_objects = tracker.update(detections, frame)

            # Precompute OCR-space bbox and largest track (used for full-frame fallback assignment).
            bbox_for_ocr_map: dict[int, tuple[int, int, int, int]] = {}
            bbox_area_map: dict[int, int] = {}
            largest_track_id: Optional[int] = None
            largest_track_area = 0
            for tracked in tracked_objects:
                scaled_bbox = scale_bbox(tracked.bbox, (proc_w, proc_h), (orig_w, orig_h))
                area = max(0, scaled_bbox[2] - scaled_bbox[0]) * max(0, scaled_bbox[3] - scaled_bbox[1])
                bbox_for_ocr_map[tracked.track_id] = scaled_bbox
                bbox_area_map[tracked.track_id] = area
                if area > largest_track_area:
                    largest_track_area = area
                    largest_track_id = tracked.track_id

            full_frame_plate_attempted = False
            full_frame_plate_text: Optional[str] = None
            full_frame_plate_crop: Optional[np.ndarray] = None

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

                # OCR/detection runs only for unseen plate tracks with retry backoff.
                last_attempt = last_ocr_attempt_frame.get(obj.track_id, -OCR_RETRY_INTERVAL_FRAMES)
                should_retry_now = (frame_count - last_attempt) >= OCR_RETRY_INTERVAL_FRAMES

                if obj.track_id not in known_plates and should_retry_now:
                    last_ocr_attempt_frame[obj.track_id] = frame_count
                    # Tracker bbox is on resized inference frame; remap to original frame for OCR quality.
                    bbox_for_ocr = bbox_for_ocr_map.get(obj.track_id, obj.bbox)
                    x1, y1, x2, y2 = bbox_for_ocr
                    bbox_area = max(0, x2 - x1) * max(0, y2 - y1)
                    debug_reason = "skipped"

                    # Run OCR gate primarily on bbox quality (class may be noisy, e.g., car -> person).
                    if effective_conf >= OCR_MIN_CONFIDENCE and bbox_area >= OCR_MIN_BBOX_AREA:
                        vehicle_crop = crop_vehicle_from_frame(original_frame, bbox_for_ocr)

                        plate_crop_yolo = plate_detector.detect_plate(vehicle_crop) if vehicle_crop is not None else None
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

                        # If local crops fail, attempt one global full-frame plate detection per frame.
                        if not plate and obj.track_id == largest_track_id:
                            if not full_frame_plate_attempted:
                                full_frame_plate_attempted = True
                                full_frame_plate_crop = plate_detector.detect_plate(original_frame)
                                full_frame_plate_text = extract_text(full_frame_plate_crop) if full_frame_plate_crop is not None else None

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
                    )
                )

            draw_detections(frame, annotated_objects, class_names=detector.class_names, min_confidence=0.5)

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
