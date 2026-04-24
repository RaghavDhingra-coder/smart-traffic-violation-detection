"""Phase 1 entry point: real-time webcam/video object detection using YOLOv8."""

from __future__ import annotations

import argparse
import platform
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
from violations.helmet import detect_no_helmet
from violations.triple_riding import detect_triple_riding

DEFAULT_FRAME_SIZE = (352, 224)
WEBCAM_FRAME_SIZE = (224, 128)
WINDOW_NAME = "Phase 2 - Object Detection + Tracking"
PLATE_DEBUG_WINDOW = "Plate Crop Debug"
OCR_MIN_BBOX_AREA = 12000
OCR_MIN_CONFIDENCE = 0.35
OCR_ALLOWED_CLASSES = {"car", "motorcycle"}
OCR_RETRY_INTERVAL_FRAMES = 30
WEBCAM_OCR_RETRY_INTERVAL_FRAMES = 45
OCR_MAX_TRACKS_PER_FRAME = 1
OCR_MAX_ATTEMPTS_PER_TRACK = 3
OCR_ENABLE_FULL_FRAME_FALLBACK = False
VEHICLE_LIKE_MIN_AREA = 30000
VEHICLE_LIKE_MIN_ASPECT = 1.20
OCR_CONFIRM_VOTES = 2
OCR_FULL_FRAME_VOTE_WEIGHT = 2
CAMERA_FRAME_READ_TIMEOUT_SEC = 5.0
VIDEO_PROCESS_EVERY_N_FRAMES = 3
WEBCAM_PROCESS_EVERY_N_FRAMES = 4
VIDEO_MAX_DETECTIONS = 20
WEBCAM_MAX_DETECTIONS = 8


@dataclass(frozen=True)
class AnnotatedTrackedObject:
    """Tracked object with optional OCR plate text for rendering."""

    track_id: Optional[int]
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
        "--disable-ocr",
        action="store_true",
        help="Disable plate detector + OCR for higher FPS.",
    )
    parser.add_argument(
        "--enable-ocr",
        action="store_true",
        help="Enable OCR in webcam mode. Off by default for smoother live preview.",
    )
    parser.add_argument(
        "--enable-tracking",
        action="store_true",
        help="Enable DeepSORT tracking and violation logic in webcam mode. Off by default for higher FPS.",
    )
    parser.add_argument(
        "--accurate-tracking",
        action="store_true",
        help="Use DeepSORT appearance embeddings for more stable IDs at the cost of lower FPS.",
    )
    return parser.parse_args()


def build_capture(source: str) -> cv2.VideoCapture:
    """
    Build a video capture with a couple of backend fallbacks.

    On macOS, explicitly trying AVFoundation helps avoid flaky default backend
    selection and camera authorization edge cases.
    """
    if source.isdigit():
        source_index = int(source)
        attempts: list[cv2.VideoCapture] = []

        if platform.system() == "Darwin":
            attempts.append(cv2.VideoCapture(source_index, cv2.CAP_AVFOUNDATION))

        attempts.append(cv2.VideoCapture(source_index))

        for capture in attempts:
            if capture.isOpened():
                # Keep webcam latency down on slower CPU-only runs.
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                return capture
            capture.release()

        return cv2.VideoCapture(source_index)

    return cv2.VideoCapture(source)


def print_capture_error(source: str) -> None:
    """Print a clearer source-specific capture failure message."""
    print("Error: Unable to open camera/video source. Check webcam connection or source path.")
    if source.isdigit():
        print("Hint: For webcam input on macOS, allow camera access for your Terminal app in")
        print("System Settings -> Privacy & Security -> Camera, then retry `python3 main.py --source 0`.")
    else:
        print(f"Hint: Verify that the file exists and is readable: {source}")


def get_runtime_settings(source: str) -> tuple[tuple[int, int], int, int, int]:
    """Use lighter defaults for webcam mode so the preview stays responsive."""
    if source.isdigit():
        return (
            WEBCAM_FRAME_SIZE,
            WEBCAM_PROCESS_EVERY_N_FRAMES,
            WEBCAM_OCR_RETRY_INTERVAL_FRAMES,
            WEBCAM_MAX_DETECTIONS,
        )
    return DEFAULT_FRAME_SIZE, VIDEO_PROCESS_EVERY_N_FRAMES, OCR_RETRY_INTERVAL_FRAMES, VIDEO_MAX_DETECTIONS


def is_ocr_enabled(args: argparse.Namespace) -> bool:
    """Keep webcam mode responsive by default; OCR stays on for file inputs."""
    if args.disable_ocr:
        return False
    if args.source.isdigit():
        return args.enable_ocr
    return True


def is_tracking_enabled(args: argparse.Namespace) -> bool:
    """Keep webcam mode responsive by default; tracking stays on for file inputs."""
    if args.source.isdigit():
        return args.enable_tracking
    return True


def main() -> None:
    args = parse_args()
    cv2.setUseOptimized(True)
    capture = build_capture(args.source)

    if not capture.isOpened():
        print_capture_error(args.source)
        capture.release()
        return

    ocr_enabled = is_ocr_enabled(args)
    tracking_enabled = is_tracking_enabled(args)

    if args.source.isdigit() and not ocr_enabled:
        print("Info: Webcam fast mode enabled. OCR is off by default to keep the live preview responsive.")
        print("Hint: Add `--enable-ocr` only if you need number plate reading and can accept lower FPS.")
    if args.source.isdigit() and not tracking_enabled:
        print("Info: Webcam fast mode keeps tracking and violation checks off by default for higher FPS.")
        print("Hint: Add `--enable-tracking` only if you need stable IDs and can accept lower FPS.")
    if tracking_enabled and not args.accurate_tracking:
        print("Info: Fast tracking mode uses motion/IoU-only association for better FPS.")
        print("Hint: Add `--accurate-tracking` if you need stronger ID persistence across occlusions.")

    try:
        frame_size, process_every_n_frames, ocr_retry_interval_frames, max_detections = get_runtime_settings(args.source)
        detector = YOLODetector(model_path=args.model, conf_threshold=args.conf, max_detections=max_detections)
        tracker = ObjectTracker(use_appearance=args.accurate_tracking) if tracking_enabled else None
        plate_detector = None if not ocr_enabled else PlateDetector()
    except Exception as exc:  # noqa: BLE001
        print(f"Error: Failed to initialize detector/tracker: {exc}")
        capture.release()
        return

    prev_time = time.perf_counter()
    last_frame_time = prev_time
    frame_count = 0
    last_processed_fps = 0.0
    last_annotated_objects: list[AnnotatedTrackedObject] = []
    # Cache successful OCR output per track.
    known_plates: dict[int, Optional[str]] = {}
    plate_votes: dict[int, dict[str, int]] = {}
    # Retry OCR periodically for tracks that previously failed (avoids one-shot misses).
    last_ocr_attempt_frame: dict[int, int] = {}
    ocr_attempt_count: dict[int, int] = {}
    # Stabilize noisy tracker metadata across frames.
    track_class_cache: dict[int, str] = {}
    track_conf_cache: dict[int, float] = {}
    debug_state_cache: dict[int, str] = {}

    try:
        while True:
            success, frame = capture.read()
            if not success:
                if args.source.isdigit() and (time.perf_counter() - last_frame_time) >= CAMERA_FRAME_READ_TIMEOUT_SEC:
                    print("Error: Camera opened but no frames arrived for 5 seconds. Exiting.")
                    print("Hint: Close other apps using the webcam, then retry with `python3 main.py --source 0 --disable-ocr`.")
                    break
                print("Info: End of stream or frame read failed. Exiting.")
                break
            last_frame_time = time.perf_counter()

            original_frame = frame
            orig_h, orig_w = original_frame.shape[:2]
            frame = cv2.resize(frame, frame_size)
            proc_h, proc_w = frame.shape[:2]

            frame_count += 1
            should_process = frame_count % process_every_n_frames == 0

            if not should_process:
                if last_annotated_objects:
                    draw_detections(frame, last_annotated_objects, class_names=detector.class_names, min_confidence=0.5)
                draw_fps(frame, last_processed_fps)
                cv2.putText(
                    frame,
                    f"Live mode: inference every {process_every_n_frames} frames",
                    (8, 34),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow(WINDOW_NAME, frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break
                continue

            detections = detector.detect(frame)

            if not tracking_enabled:
                annotated_objects = [
                    AnnotatedTrackedObject(
                        track_id=None,
                        class_id=det.class_id,
                        confidence=det.confidence,
                        bbox=det.bbox,
                    )
                    for det in detections
                ]
                last_annotated_objects = annotated_objects
                draw_detections(frame, annotated_objects, class_names=detector.class_names, min_confidence=0.5)

                current_time = time.perf_counter()
                fps = 1.0 / max(current_time - prev_time, 1e-6)
                prev_time = current_time
                last_processed_fps = fps
                draw_fps(frame, last_processed_fps)
                cv2.putText(
                    frame,
                    f"Fast webcam mode: detect every {process_every_n_frames} frames",
                    (8, 34),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow(WINDOW_NAME, frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break
                continue

            tracked_objects = tracker.update(detections, frame)

            # Phase 4: violation detection on tracked objects.
            triple_v = detect_triple_riding(tracked_objects)
            helmet_v = detect_no_helmet(tracked_objects)
            all_violations = triple_v + helmet_v

            # track_id -> violation text, merge multiple violations if needed.
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

            # Keep OCR cost bounded: only a small number of largest tracks get OCR attempts per frame.
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

                # OCR/detection runs only for unseen plate tracks with retry backoff.
                last_attempt = last_ocr_attempt_frame.get(obj.track_id, -ocr_retry_interval_frames)
                should_retry_now = (frame_count - last_attempt) >= ocr_retry_interval_frames
                attempts_so_far = ocr_attempt_count.get(obj.track_id, 0)
                is_vehicle_candidate = class_name in OCR_ALLOWED_CLASSES or is_vehicle_like_bbox(obj.bbox)
                is_prioritized = obj.track_id in prioritized_track_set

                if (
                    ocr_enabled
                    and obj.track_id not in known_plates
                    and should_retry_now
                    and attempts_so_far < OCR_MAX_ATTEMPTS_PER_TRACK
                    and is_vehicle_candidate
                    and is_prioritized
                ):
                    last_ocr_attempt_frame[obj.track_id] = frame_count
                    ocr_attempt_count[obj.track_id] = attempts_so_far + 1
                    # Tracker bbox is on resized inference frame; remap to original frame for OCR quality.
                    bbox_for_ocr = bbox_for_ocr_map.get(obj.track_id, obj.bbox)
                    x1, y1, x2, y2 = bbox_for_ocr
                    bbox_area = max(0, x2 - x1) * max(0, y2 - y1)
                    debug_reason = "skipped"

                    # Run OCR gate primarily on bbox quality (class may be noisy, e.g., car -> person).
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

                        # If local crops fail, attempt one global full-frame plate detection per frame.
                        if OCR_ENABLE_FULL_FRAME_FALLBACK and not plate and obj.track_id == largest_track_id:
                            if not full_frame_plate_attempted:
                                full_frame_plate_attempted = True
                                full_frame_plate_crop = (
                                    plate_detector.detect_plate(original_frame)
                                    if plate_detector is not None
                                    else None
                                )
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
                        violation=violation_map.get(obj.track_id),
                    )
                )

            last_annotated_objects = annotated_objects
            draw_detections(frame, annotated_objects, class_names=detector.class_names, min_confidence=0.5)

            current_time = time.perf_counter()
            fps = 1.0 / max(current_time - prev_time, 1e-6)
            prev_time = current_time
            last_processed_fps = fps
            draw_fps(frame, last_processed_fps)
            if args.source.isdigit():
                cv2.putText(
                    frame,
                    f"Live mode: inference every {process_every_n_frames} frames",
                    (8, 34),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

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
