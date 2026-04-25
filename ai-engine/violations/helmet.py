"""Helmet violation detection with safe fallback behavior."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np

# Keep Ultralytics cache/config within project to avoid user-profile permission issues.
_PROJECT_DIR = Path(__file__).resolve().parent.parent
_ULTRALYTICS_DIR = _PROJECT_DIR / ".ultralytics"
_ULTRALYTICS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(_ULTRALYTICS_DIR))

from ultralytics import YOLO

DEFAULT_HELMET_MODEL_PATH = "helmet_best.pt"
PERSON_CLASS_ID = 0
BIKE_CLASS_IDS = {1, 3}
WITH_HELMET_LABELS = {"helmet", "with helmet"}
WITHOUT_HELMET_LABELS = {"no helmet", "without helmet", "without_helmet", "no_helmet"}
HELMET_CONFIDENCE_THRESHOLD = 0.60
HEAD_REGION_HEIGHT_RATIO = 0.55
HEAD_REGION_WIDTH_PAD_RATIO = 0.12


def _intersection_area(b1: tuple[int, int, int, int], b2: tuple[int, int, int, int]) -> int:
    """Return intersection area between two boxes in xyxy format."""
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])
    if x2 <= x1 or y2 <= y1:
        return 0
    return (x2 - x1) * (y2 - y1)


def _expanded_rider_region(mbox: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Expand motorcycle bbox upward to better cover the rider region."""
    x1, y1, x2, y2 = mbox
    h = max(1, y2 - y1)
    return (x1, max(0, y1 - int(h * 0.85)), x2, y2)


def _is_rider_associated(
    person_box: tuple[int, int, int, int],
    bike_box: tuple[int, int, int, int],
) -> bool:
    """Associate a rider to a motorcycle using overlap or bottom-center containment."""
    rider_region = _expanded_rider_region(bike_box)
    if _intersection_area(person_box, rider_region) > 0:
        return True

    px = (person_box[0] + person_box[2]) // 2
    py = person_box[3]
    rx1, ry1, rx2, ry2 = rider_region
    return rx1 <= px <= rx2 and ry1 <= py <= ry2


class HelmetDetector:
    """Wrap a trained YOLO helmet model with graceful fallback when unavailable."""

    def __init__(
        self,
        model_path: str = DEFAULT_HELMET_MODEL_PATH,
        conf_threshold: float = HELMET_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.conf_threshold = conf_threshold
        self.model = None
        self.is_available = False
        self.class_names: dict[int, str] = {}

        resolved_model_path = self._resolve_model_path(model_path)
        self.model_path = resolved_model_path
        if resolved_model_path is None:
            return

        try:
            self.model = YOLO(str(resolved_model_path))
            try:
                self.model.fuse()
            except Exception:  # noqa: BLE001
                pass
            self.class_names = {
                int(idx): str(name).strip().lower()
                for idx, name in dict(self.model.names).items()
            }
            self.is_available = True
        except Exception:  # noqa: BLE001
            self.model = None
            self.is_available = False

    @staticmethod
    def _resolve_model_path(model_path: str) -> Optional[Path]:
        path = Path(model_path)
        if path.exists():
            return path

        project_relative = _PROJECT_DIR / model_path
        if project_relative.exists():
            return project_relative

        return None

    @staticmethod
    def _crop_head_region(frame: np.ndarray, bbox: tuple[int, int, int, int]) -> Optional[np.ndarray]:
        if frame is None or frame.size == 0:
            return None

        frame_h, frame_w = frame.shape[:2]
        x1, y1, x2, y2 = bbox
        x1 = max(0, min(x1, frame_w - 1))
        y1 = max(0, min(y1, frame_h - 1))
        x2 = max(0, min(x2, frame_w))
        y2 = max(0, min(y2, frame_h))
        if x2 <= x1 or y2 <= y1:
            return None

        w = x2 - x1
        h = y2 - y1
        pad_x = int(w * HEAD_REGION_WIDTH_PAD_RATIO)
        head_y2 = y1 + int(h * HEAD_REGION_HEIGHT_RATIO)

        hx1 = max(0, x1 - pad_x)
        hx2 = min(frame_w, x2 + pad_x)
        hy1 = y1
        hy2 = max(hy1 + 1, min(frame_h, head_y2))
        if hx2 <= hx1 or hy2 <= hy1:
            return None

        crop = frame[hy1:hy2, hx1:hx2]
        if crop.size == 0:
            return None
        return crop

    def predicts_no_helmet(self, frame: np.ndarray, rider_bbox: tuple[int, int, int, int]) -> bool:
        """Return True only when the model explicitly predicts no-helmet."""
        if not self.is_available or self.model is None:
            return False

        crop = self._crop_head_region(frame, rider_bbox)
        if crop is None:
            return False

        try:
            results = self.model(crop, conf=self.conf_threshold, verbose=False)
        except Exception:  # noqa: BLE001
            return False

        if not results:
            return False

        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return False

        best_with = 0.0
        best_without = 0.0
        for box in boxes:
            class_id = int(box.cls.item())
            label = self.class_names.get(class_id, str(class_id))
            confidence = float(box.conf.item())
            if label in WITH_HELMET_LABELS:
                best_with = max(best_with, confidence)
            elif label in WITHOUT_HELMET_LABELS:
                best_without = max(best_without, confidence)

        return best_without >= self.conf_threshold and best_without > (best_with + 0.15)

    def batch_predict_helmets(
        self,
        frame: np.ndarray,
        rider_bboxes: list[tuple[int, int, int, int]],
    ) -> list[bool]:
        """
        Detect helmets for multiple riders efficiently.

        Returns list of bools, one per rider (True = no helmet detected).
        """
        if not self.is_available or self.model is None or not rider_bboxes:
            return [False] * len(rider_bboxes)

        results_list = []
        for bbox in rider_bboxes:
            results_list.append(self.predicts_no_helmet(frame, bbox))

        return results_list


def _placeholder_detect_no_helmet(tracked_objects: Iterable[Any]) -> list[dict[str, Any]]:
    """Fallback heuristic used when the trained helmet model is unavailable."""
    objects = list(tracked_objects or [])
    if not objects:
        return []

    persons = [obj for obj in objects if getattr(obj, "class_id", -1) == PERSON_CLASS_ID]
    motorcycles = [obj for obj in objects if getattr(obj, "class_id", -1) in BIKE_CLASS_IDS]

    violations: list[dict[str, Any]] = []
    for motorcycle in motorcycles:
        mbox = getattr(motorcycle, "bbox", None)
        if mbox is None:
            continue

        has_rider = False
        for person in persons:
            pbox = getattr(person, "bbox", None)
            if pbox is None:
                continue
            if _intersection_area(mbox, pbox) > 0:
                has_rider = True
                break

        if has_rider:
            violations.append(
                {
                    "track_id": int(getattr(motorcycle, "track_id", -1)),
                    "type": "NO_HELMET",
                }
            )

    return violations


# Global cache for helmet violation status per track
_helmet_violation_cache: dict[int, bool] = {}
_helmet_cache_ttl: dict[int, int] = {}  # frame count
_helmet_check_frame_count: dict[int, int] = {}  # track how many frames we've checked without finding violation


def detect_no_helmet(
    tracked_objects: Iterable[Any],
    frame: Optional[np.ndarray] = None,
    helmet_detector: Optional[HelmetDetector] = None,
    frame_count: int = 0,
    cache_ttl_frames: int = 15,
    max_check_frames: int = 60,
) -> list[dict[str, Any]]:
    """
    Detect helmet violations using the trained YOLO model when available.

    Falls back to the previous heuristic if no model/frame is available.
    Uses caching to skip redundant checks on stable tracks.
    Stops checking tracks after max_check_frames if no violation is found.

    Args:
        tracked_objects: Objects to check
        frame: Frame for helmet detection
        helmet_detector: Helmet model detector
        frame_count: Current frame number (used for cache TTL)
        cache_ttl_frames: Frames to cache helmet status before re-checking (default: 15)
        max_check_frames: Stop checking track after this many frames without violation (default: 60)
    """
    global _helmet_violation_cache, _helmet_cache_ttl, _helmet_check_frame_count

    objects = list(tracked_objects or [])
    if not objects:
        return []

    if (
        helmet_detector is None
        or not helmet_detector.is_available
        or frame is None
        or frame.size == 0
    ):
        return _placeholder_detect_no_helmet(objects)

    # Clean stale cache entries
    current_frames = set(int(getattr(obj, "track_id", -1)) for obj in objects if int(getattr(obj, "track_id", -1)) >= 0)
    for track_id in list(_helmet_cache_ttl.keys()):
        if track_id not in current_frames or (frame_count - _helmet_cache_ttl[track_id]) > cache_ttl_frames:
            _helmet_violation_cache.pop(track_id, None)
            _helmet_cache_ttl.pop(track_id, None)
            _helmet_check_frame_count.pop(track_id, None)

    persons = [obj for obj in objects if getattr(obj, "class_id", -1) == PERSON_CLASS_ID]
    motorcycles = [obj for obj in objects if getattr(obj, "class_id", -1) in BIKE_CLASS_IDS]

    violations: list[dict[str, Any]] = []
    for motorcycle in motorcycles:
        mbox = getattr(motorcycle, "bbox", None)
        track_id = int(getattr(motorcycle, "track_id", -1))
        if mbox is None or track_id < 0:
            continue

        # Check if we've already determined this track is clean (no violation after max_check_frames)
        check_count = _helmet_check_frame_count.get(track_id, 0)
        if check_count >= max_check_frames and track_id not in _helmet_violation_cache:
            # Stop checking this track
            _helmet_violation_cache[track_id] = False
            continue

        # Check cache first
        if track_id in _helmet_violation_cache:
            if _helmet_violation_cache[track_id]:
                violations.append(
                    {
                        "track_id": track_id,
                        "type": "NO_HELMET",
                    }
                )
            continue

        associated_riders = [
            person
            for person in persons
            if getattr(person, "bbox", None) is not None
            and _is_rider_associated(getattr(person, "bbox"), mbox)
        ]
        if not associated_riders:
            _helmet_violation_cache[track_id] = False
            _helmet_cache_ttl[track_id] = frame_count
            _helmet_check_frame_count[track_id] = check_count + 1
            continue

        # Increment frame count for this track
        _helmet_check_frame_count[track_id] = check_count + 1

        # Batch detect helmets for all riders
        rider_bboxes = [getattr(rider, "bbox") for rider in associated_riders]
        helmet_results = helmet_detector.batch_predict_helmets(frame, rider_bboxes)

        has_violation = any(helmet_results)
        _helmet_violation_cache[track_id] = has_violation
        _helmet_cache_ttl[track_id] = frame_count

        if has_violation:
            violations.append(
                {
                    "track_id": track_id,
                    "type": "NO_HELMET",
                }
            )

    return violations
