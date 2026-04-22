"""Phase 1 entry point: real-time webcam/video object detection using YOLOv8."""

from __future__ import annotations

import argparse
import time

import cv2

from detector import YOLODetector
from tracker import ObjectTracker
from utils import draw_detections, draw_fps

FRAME_SIZE = (416, 256)
WINDOW_NAME = "Phase 2 - Object Detection + Tracking"


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
    except Exception as exc:  # noqa: BLE001
        print(f"Error: Failed to initialize detector/tracker: {exc}")
        capture.release()
        return

    prev_time = time.perf_counter()
    frame_count = 0

    try:
        while True:
            success, frame = capture.read()
            if not success:
                print("Info: End of stream or frame read failed. Exiting.")
                break

            # Optimization 1: smaller frame for faster inference.
            frame = cv2.resize(frame, FRAME_SIZE)

            # Optimization 2: run detector/tracker on every second frame.
            frame_count += 1
            if frame_count % 2 != 0:
                continue

            detections = detector.detect(frame)
            tracked_objects = tracker.update(detections, frame)

            draw_detections(frame, tracked_objects, class_names=detector.class_names, min_confidence=0.5)

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
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
