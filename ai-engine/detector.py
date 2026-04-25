"""YOLOv8 detector module for Phase 1 real-time object detection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

import numpy as np

# Keep Ultralytics cache/config within project to avoid user-profile permission issues.
_PROJECT_DIR = Path(__file__).resolve().parent
_ULTRALYTICS_DIR = _PROJECT_DIR / ".ultralytics"
_ULTRALYTICS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(_ULTRALYTICS_DIR))

from ultralytics import YOLO

# YOLO class IDs (COCO)
TARGET_CLASS_IDS = {0, 2, 3}
VEHICLE_CLASS_IDS = {2, 3, 5, 7}
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
        target_class_ids: Optional[Set[int]] = None,
    ) -> None:
        self.model_path = self._resolve_model_path(model_path)
        self.conf_threshold = conf_threshold
        self.max_detections = max_detections
        self.target_class_ids = set(target_class_ids) if target_class_ids is not None else set(TARGET_CLASS_IDS)
        self.model = YOLO(self.model_path)
        try:
            self.model.fuse()
        except Exception:  # noqa: BLE001
            pass

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
        results = self.model(
            frame,
            conf=self.conf_threshold,
            max_det=self.max_detections,
            classes=sorted(self.target_class_ids),
            verbose=False,
        )
        if not results:
            return []

        detections: List[Detection] = []
        result = results[0]

        for box in result.boxes:
            class_id = int(box.cls.item())
            if class_id not in self.target_class_ids:
                continue

            confidence = float(box.conf.item())
            # Optimization 4: strict pre-tracker confidence filtering.
            if confidence < self.conf_threshold:
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


_VEHICLE_ONLY_DETECTOR: Optional[YOLODetector] = None


def detect_vehicles(frame: np.ndarray) -> List[Detection]:
    """Required helper: vehicle-only detections (car/motorcycle/bus/truck)."""
    global _VEHICLE_ONLY_DETECTOR
    if _VEHICLE_ONLY_DETECTOR is None:
        _VEHICLE_ONLY_DETECTOR = YOLODetector(
            model_path=DEFAULT_MODEL_PATH,
            conf_threshold=0.35,
            max_detections=50,
            target_class_ids=VEHICLE_CLASS_IDS,
        )
    return _VEHICLE_ONLY_DETECTOR.detect(frame)
