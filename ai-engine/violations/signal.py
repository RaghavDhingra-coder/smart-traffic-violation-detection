"""Signal detection + red-light stop-line violation logic."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

import cv2
import numpy as np

_CLASS_ID_TO_NAME = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}
_ALLOWED_CLASSES = {"car", "motorcycle", "bus", "truck"}

Point = tuple[int, int]


@dataclass
class SignalStabilityState:
    # NEW: counters for stable signal classification to avoid flicker.
    red_count: int = 0
    green_count: int = 0
    unknown_count: int = 0
    signal_state: str = "UNKNOWN"


# NEW: module-level stability state for continuous video inference.
_SIGNAL_STABILITY = SignalStabilityState()


def get_centroid(bbox: tuple[int, int, int, int]) -> Point:
    """Return centroid (x, y) from (x1, y1, x2, y2)."""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def get_reference_point(bbox: tuple[int, int, int, int], crossing_point: str = "centroid") -> Point:
    """Return either centroid or bottom-center point from bbox."""
    x1, y1, x2, y2 = bbox
    mode = str(crossing_point).strip().lower()
    if mode == "bottom":
        return ((x1 + x2) // 2, y2)
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def check_line_crossing(
    prev_y: int,
    curr_y: int,
    line_y: int,
    direction: str = "both",
) -> bool:
    # NEW: support scene-dependent crossing direction.
    direction = str(direction).strip().lower()
    crossed_up = prev_y > line_y and curr_y <= line_y
    crossed_down = prev_y < line_y and curr_y >= line_y
    if direction == "up":
        return crossed_up
    if direction == "down":
        return crossed_down
    return crossed_up or crossed_down


def detect_violation(
    track_id: int,
    history: list[Point],
    signal_state: str,
    line_y: int,
    crossing_direction: str = "both",
    line_buffer: int = 0,
    allow_start_below: bool = False,
    start_below_confirm_frames: int = 2,
    stationary_motion_px: int = 3,
) -> bool:
    _ = track_id
    if signal_state != "RED":
        return False

    if len(history) < 2:
        return False

    upper_line = int(line_y) - max(0, int(line_buffer))
    lower_line = int(line_y) + max(0, int(line_buffer))

    prev_y = history[-2][1]
    curr_y = history[-1][1]

    crossed_up = prev_y > lower_line and curr_y <= upper_line
    crossed_down = prev_y < upper_line and curr_y >= lower_line

    direction = str(crossing_direction).strip().lower()
    if direction == "up" and crossed_up:
        return True
    if direction == "down" and crossed_down:
        return True
    if direction == "both" and (crossed_up or crossed_down):
        return True

    if not allow_start_below:
        return False

    if len(history) < max(1, int(start_below_confirm_frames)):
        return False

    first_y = history[0][1]
    motion = abs(history[-1][1] - history[0][1])
    if motion < max(0, int(stationary_motion_px)):
        return False

    if direction == "down":
        return first_y >= lower_line
    if direction == "up":
        return first_y <= upper_line
    return first_y >= lower_line or first_y <= upper_line


def _clip_roi(
    frame: np.ndarray,
    roi: tuple[int, int, int, int],
) -> tuple[int, int, int, int, np.ndarray]:
    x1, y1, x2, y2 = roi
    h, w = frame.shape[:2]

    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(x1 + 1, min(x2, w))
    y2 = max(y1 + 1, min(y2, h))

    return x1, y1, x2, y2, frame[y1:y2, x1:x2]


def _classify_raw_signal(
    roi_frame: np.ndarray,
) -> tuple[str, np.ndarray, np.ndarray, float, float, float, float]:
    # NEW: HSV signal detection using required thresholds + Gaussian blur.
    blurred = cv2.GaussianBlur(roi_frame, (5, 5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0, 100, 100], dtype=np.uint8)
    upper_red1 = np.array([10, 255, 255], dtype=np.uint8)
    lower_red2 = np.array([160, 100, 100], dtype=np.uint8)
    upper_red2 = np.array([180, 255, 255], dtype=np.uint8)

    # NEW: slightly wider green hue range to handle camera tint/compression.
    lower_green = np.array([35, 60, 60], dtype=np.uint8)
    upper_green = np.array([95, 255, 255], dtype=np.uint8)

    red_mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
    green_mask = cv2.inRange(hsv, lower_green, upper_green)

    # NEW: denoise masks so small scattered pixels do not dominate decisions.
    kernel = np.ones((3, 3), dtype=np.uint8)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    total_pixels = float(max(1, roi_frame.shape[0] * roi_frame.shape[1]))
    red_ratio = float(np.count_nonzero(red_mask)) / total_pixels
    green_ratio = float(np.count_nonzero(green_mask)) / total_pixels

    # NEW: lamp-zone scoring (top third as RED lamp, bottom third as GREEN lamp).
    h = roi_frame.shape[0]
    top_h = max(1, h // 3)
    bot_y = max(0, h - top_h)

    red_top = red_mask[:top_h, :]
    green_bottom = green_mask[bot_y:, :]
    red_top_ratio = float(np.count_nonzero(red_top)) / float(max(1, red_top.size))
    green_bottom_ratio = float(np.count_nonzero(green_bottom)) / float(max(1, green_bottom.size))

    # NEW: blob-based scoring is more reliable than pure pixel ratio.
    def _largest_component_score(mask: np.ndarray, expected: str) -> float:
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        if num_labels <= 1:
            return 0.0
        best = 0.0
        for idx in range(1, num_labels):
            area = float(stats[idx, cv2.CC_STAT_AREA])
            if area < 6:  # tiny noise
                continue
            w_box = float(stats[idx, cv2.CC_STAT_WIDTH])
            h_box = float(stats[idx, cv2.CC_STAT_HEIGHT])
            if h_box <= 0:
                continue
            aspect = w_box / h_box
            if aspect > 3.0 or aspect < 0.33:
                continue
            cy = float(centroids[idx][1]) / float(max(1, h))
            # Position prior: red expected upper region, green lower-middle.
            if expected == "red":
                pos_weight = 1.0 if cy <= 0.62 else 0.45
            else:
                pos_weight = 1.0 if cy >= 0.28 else 0.45
            score = (area / max(1.0, total_pixels)) * pos_weight
            best = max(best, score)
        return best

    red_blob_score = _largest_component_score(red_mask, expected="red")
    green_blob_score = _largest_component_score(green_mask, expected="green")

    # NEW: keep a tie/deadband so transitions do not get forced into RED.
    ratio_gap = abs(red_ratio - green_ratio)
    raw_state = "UNKNOWN"
    if green_blob_score > max(0.0015, red_blob_score * 1.25) and green_ratio > 0.006:
        raw_state = "GREEN"
    elif red_blob_score > max(0.0015, green_blob_score * 1.25) and red_ratio > 0.006:
        raw_state = "RED"
    elif green_bottom_ratio > (red_top_ratio * 1.35) and green_bottom_ratio > 0.006:
        raw_state = "GREEN"
    elif red_top_ratio > (green_bottom_ratio * 1.35) and red_top_ratio > 0.006:
        raw_state = "RED"
    elif green_ratio > max(0.010, red_ratio * 1.20):
        raw_state = "GREEN"
    elif red_ratio > max(0.010, green_ratio * 1.20):
        raw_state = "RED"
    elif ratio_gap < 0.004:
        raw_state = "UNKNOWN"

    return raw_state, red_mask, green_mask, red_ratio, green_ratio, red_top_ratio, green_bottom_ratio


def get_signal_state(
    frame: np.ndarray,
    roi: tuple[int, int, int, int],
    stability_frames: int = 3,
    red_ratio_threshold: float = 0.006,
    return_debug: bool = False,
) -> str | tuple[str, dict[str, Any]]:
    """
    # NEW: Stable signal state detection from ROI.

    Returns RED/GREEN/UNKNOWN with temporal stability:
    - RED needs >= stability_frames consecutive raw RED
    - GREEN needs >= stability_frames consecutive raw GREEN
    """
    _ = red_ratio_threshold
    x1, y1, x2, y2, roi_frame = _clip_roi(frame, roi)
    if roi_frame.size == 0:
        if return_debug:
            return "UNKNOWN", {
                "roi": np.zeros((1, 1, 3), dtype=np.uint8),
                "red_mask": np.zeros((1, 1), dtype=np.uint8),
                "green_mask": np.zeros((1, 1), dtype=np.uint8),
                "raw_state": "UNKNOWN",
                "red_ratio": 0.0,
                "green_ratio": 0.0,
                "roi_coords": (x1, y1, x2, y2),
            }
        return "UNKNOWN"

    raw_state, red_mask, green_mask, red_ratio, green_ratio, red_top_ratio, green_bottom_ratio = _classify_raw_signal(
        roi_frame
    )

    # NEW: strict consecutive-frame stability logic (no long-tail inertia).
    if raw_state == "RED":
        _SIGNAL_STABILITY.red_count += 1
        _SIGNAL_STABILITY.green_count = 0
        _SIGNAL_STABILITY.unknown_count = 0
    elif raw_state == "GREEN":
        _SIGNAL_STABILITY.green_count += 1
        _SIGNAL_STABILITY.red_count = 0
        _SIGNAL_STABILITY.unknown_count = 0
    else:
        _SIGNAL_STABILITY.unknown_count += 1
        _SIGNAL_STABILITY.red_count = 0
        _SIGNAL_STABILITY.green_count = 0

    if _SIGNAL_STABILITY.red_count >= stability_frames:
        _SIGNAL_STABILITY.signal_state = "RED"
    elif _SIGNAL_STABILITY.green_count >= stability_frames:
        _SIGNAL_STABILITY.signal_state = "GREEN"
    elif _SIGNAL_STABILITY.unknown_count >= stability_frames:
        _SIGNAL_STABILITY.signal_state = "UNKNOWN"

    if return_debug:
        return _SIGNAL_STABILITY.signal_state, {
            "roi": roi_frame,
            "red_mask": red_mask,
            "green_mask": green_mask,
            "raw_state": raw_state,
            "red_ratio": red_ratio,
            "green_ratio": green_ratio,
            "red_top_ratio": red_top_ratio,
            "green_bottom_ratio": green_bottom_ratio,
            "roi_coords": (x1, y1, x2, y2),
        }

    return _SIGNAL_STABILITY.signal_state


class RedLightViolationEngine:
    """Stateful red-light violation detector with evidence + JSON logging."""

    def __init__(self) -> None:
        # NEW: required tracking memory + duplicate prevention.
        self.track_history: dict[int, list[Point]] = defaultdict(list)
        self.violated_ids: set[int] = set()
        self._history_size = 64

    @staticmethod
    def _save_evidence(frame: np.ndarray, track_id: int, evidence_dir: str) -> tuple[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        out_dir = Path(evidence_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        image_path = out_dir / f"track_{track_id}_{timestamp}.jpg"
        cv2.imwrite(str(image_path), frame)
        return str(image_path), timestamp

    @staticmethod
    def _append_json_log(json_log_path: str, payload: dict[str, Any]) -> None:
        out_path = Path(json_log_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload) + "\n")

    def update(
        self,
        tracked_objects: Iterable[Any],
        stop_line_y: int,
        signal_state: str,
        crossing_direction: str = "both",
        line_buffer: int = 0,
        crossing_point: str = "centroid",
        allow_start_below: bool = False,
        start_below_confirm_frames: int = 2,
        stationary_motion_px: int = 3,
        frame: Optional[np.ndarray] = None,
        save_evidence: bool = True,
        evidence_dir: str = "violations",
        json_log_path: str = "violations/violations.jsonl",
    ) -> list[dict[str, Any]]:
        violations: list[dict[str, Any]] = []

        for obj in tracked_objects or []:
            track_id = int(getattr(obj, "track_id", -1))
            class_id = int(getattr(obj, "class_id", -1))
            class_name = str(getattr(obj, "class_name", _CLASS_ID_TO_NAME.get(class_id, "")))
            bbox = getattr(obj, "bbox", None)
            if track_id < 0 or class_name not in _ALLOWED_CLASSES or bbox is None or len(bbox) != 4:
                continue

            centroid = get_reference_point(tuple(map(int, bbox)), crossing_point=crossing_point)
            history = self.track_history[track_id]
            history.append(centroid)
            if len(history) > self._history_size:
                del history[:-self._history_size]

            if track_id in self.violated_ids:
                continue

            if not detect_violation(
                track_id,
                history,
                signal_state,
                stop_line_y,
                crossing_direction=crossing_direction,
                line_buffer=line_buffer,
                allow_start_below=allow_start_below,
                start_below_confirm_frames=start_below_confirm_frames,
                stationary_motion_px=stationary_motion_px,
            ):
                continue

            payload: dict[str, Any] = {
                "track_id": track_id,
                "type": "SIGNAL_VIOLATION",
                "signal_state": signal_state,
            }

            if save_evidence and frame is not None:
                evidence_path, timestamp = self._save_evidence(frame, track_id, evidence_dir=evidence_dir)
                payload["evidence_path"] = evidence_path
                payload["timestamp"] = timestamp

            if save_evidence:
                self._append_json_log(json_log_path=json_log_path, payload=payload)

            self.violated_ids.add(track_id)
            violations.append(payload)

        return violations


_ENGINE = RedLightViolationEngine()


def detect_signal_violation(
    tracked_objects: Iterable[Any],
    stop_line_y: int,
    signal_state: str,
    crossing_direction: str = "both",
    line_buffer: int = 0,
    crossing_point: str = "centroid",
    allow_start_below: bool = False,
    start_below_confirm_frames: int = 2,
    confirmation_frames: int = 2,
    stationary_motion_px: int = 3,
    frame: Optional[np.ndarray] = None,
    save_evidence: bool = True,
    evidence_dir: str = "violations",
    json_log_path: str = "violations/violations.jsonl",
) -> list[dict[str, Any]]:
    """Backward-compatible wrapper around the stateful red-light engine."""
    _ = confirmation_frames
    return _ENGINE.update(
        tracked_objects=tracked_objects,
        stop_line_y=stop_line_y,
        signal_state=signal_state,
        crossing_direction=crossing_direction,
        line_buffer=line_buffer,
        crossing_point=crossing_point,
        allow_start_below=allow_start_below,
        start_below_confirm_frames=start_below_confirm_frames,
        stationary_motion_px=stationary_motion_px,
        frame=frame,
        save_evidence=save_evidence,
        evidence_dir=evidence_dir,
        json_log_path=json_log_path,
    )


def get_track_history() -> dict[int, list[Point]]:
    return dict(_ENGINE.track_history)


def get_violated_ids() -> set[int]:
    return set(_ENGINE.violated_ids)
