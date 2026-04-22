"""YOLOv8 detector module for Phase 1 real-time object detection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
from ultralytics import YOLO

# YOLO class IDs (COCO)
TARGET_CLASS_IDS = {0, 2, 3}
DEFAULT_MODEL_PATH = "yolov8n.pt"


@dataclass(frozen=True)
class Detection:
    """Represents a single filtered detection."""

    class_id: int
    class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]


class YOLODetector:
    """Wrapper around Ultralytics YOLO model with class filtering."""

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        conf_threshold: float = 0.6,
        max_detections: int = 20,
    ) -> None:
        self.model_path = self._resolve_model_path(model_path)
        self.conf_threshold = conf_threshold
        self.max_detections = max_detections
        self.model = YOLO(self.model_path)

        # Keep names as a plain dict for fast lookup and future extension.
        self.class_names: Dict[int, str] = dict(self.model.names)

    @staticmethod
    def _resolve_model_path(model_path: str) -> str:
        """Prefer local model file path if present; fall back to model name for auto-download."""
        path = Path(model_path)
        if path.exists():
            return str(path)
        return model_path

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run inference and return only person, car, and motorcycle detections."""
        # Optimization 3: higher confidence + capped detections reduce compute and clutter.
        results = self.model(frame, conf=self.conf_threshold, max_det=self.max_detections, verbose=False)
        if not results:
            return []

        detections: List[Detection] = []
        result = results[0]

        for box in result.boxes:
            class_id = int(box.cls.item())
            if class_id not in TARGET_CLASS_IDS:
                continue

            confidence = float(box.conf.item())
            # Optimization 4: strict pre-tracker confidence filtering.
            if confidence <= 0.5:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            class_name = self.class_names.get(class_id, str(class_id))

            detections.append(
                Detection(
                    class_id=class_id,
                    class_name=class_name,
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2),
                )
            )

        return detections
