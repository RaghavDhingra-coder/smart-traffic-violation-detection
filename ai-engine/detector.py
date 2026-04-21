# TODO for violation-detector: replace heuristic stubs with trained classes, tracking, and zone-aware business rules.
import base64
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


class ViolationDetector:
    def __init__(self) -> None:
        model_path = Path("models/best.pt")
        selected_model = str(model_path) if model_path.exists() else "yolov8n.pt"
        # STUB: replace with real implementation by loading a violation-specific YOLOv8 model.
        self.model = YOLO(selected_model)
        self.no_parking_zone = np.array([[40, 40], [500, 40], [500, 300], [40, 300]], dtype=np.int32)

    def detect(self, image: np.ndarray) -> list[dict]:
        height, width = image.shape[:2]
        detections: list[dict] = []

        # STUB: replace with real implementation that maps YOLO detections to violation classes.
        mock_plate_crop = image[max(0, height // 4):max(height // 4 + 80, 80), max(0, width // 4):max(width // 4 + 180, 180)]
        detections.append(
            {
                "violation_type": "no_helmet",
                "confidence": 0.91,
                "bbox": [50, 50, min(width - 20, 280), min(height - 20, 260)],
                "plate_crop": mock_plate_crop,
            }
        )

        # STUB: replace with real implementation for multi-rider detection and person counting.
        detections.append(
            {
                "violation_type": "trippling",
                "confidence": 0.78,
                "bbox": [max(10, width // 3), max(10, height // 3), min(width - 20, width // 3 + 220), min(height - 20, height // 3 + 180)],
                "plate_crop": mock_plate_crop,
            }
        )

        # STUB: replace with real implementation using calibrated parking polygons and object persistence.
        centroid = (width // 2, height // 2)
        zone_hit = cv2.pointPolygonTest(self.no_parking_zone, centroid, False) >= 0
        if zone_hit:
            detections.append(
                {
                    "violation_type": "no_parking",
                    "confidence": 0.66,
                    "bbox": [80, max(20, height // 2 - 80), min(width - 20, 360), min(height - 20, height // 2 + 120)],
                    "plate_crop": mock_plate_crop,
                }
            )

        return detections

    def annotate_frame(self, image: np.ndarray, detections: list[dict]) -> str:
        annotated = image.copy()
        cv2.polylines(annotated, [self.no_parking_zone], True, (0, 165, 255), 2)

        for detection in detections:
            x1, y1, x2, y2 = detection["bbox"]
            label = f"{detection['violation_type']} ({detection['confidence']:.2f})"
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(annotated, label, (x1, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        success, buffer = cv2.imencode(".jpg", annotated)
        if not success:
            return ""
        return base64.b64encode(buffer.tobytes()).decode("utf-8")
