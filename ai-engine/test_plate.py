"""Quick local test for the trained license plate detector + OCR pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from ocr import extract_text, normalize_plate_text
from plate_detector import DEFAULT_PLATE_MODEL_PATH
from ultralytics import YOLO

AI_ENGINE_DIR = Path(__file__).resolve().parent


def resolve_ai_engine_path(path_text: str) -> Path:
    """Resolve relative paths from ai-engine/ so the script works from any cwd."""
    path = Path(path_text)
    if path.is_absolute():
        return path
    return AI_ENGINE_DIR / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test license plate detection on one image")
    parser.add_argument(
        "--image",
        default="test_copy.jpg",
        help="Input image path. Relative paths are resolved from ai-engine/.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_PLATE_MODEL_PATH,
        help="Plate YOLO model path. Relative paths are resolved from ai-engine/.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.10,
        help="Plate detection confidence threshold.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show annotated image window.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_path = resolve_ai_engine_path(args.model)
    image_path = resolve_ai_engine_path(args.image)

    if not model_path.exists():
        raise FileNotFoundError(f"Plate model not found: {model_path}")
    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    model = YOLO(str(model_path))
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"OpenCV could not read image: {image_path}")

    results = model(image, conf=args.conf, verbose=False)
    detections = 0
    readable = 0

    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            plate_crop = image[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
            if plate_crop.size == 0:
                continue

            detections += 1
            raw_text = extract_text(plate_crop)
            confidence = float(box.conf.item())

            if raw_text:
                readable += 1
                plate_number = normalize_plate_text(raw_text)
                print(f"Detected License Plate: {plate_number} (conf={confidence:.2f})")
            else:
                print(f"Plate detected but no readable OCR text (conf={confidence:.2f})")

    if detections == 0:
        print("No plate detected.")
    elif readable == 0:
        print(f"Detected {detections} plate region(s), but OCR did not read a valid plate.")

    if args.show and results:
        cv2.imshow("Plate Detection Output", results[0].plot())
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
