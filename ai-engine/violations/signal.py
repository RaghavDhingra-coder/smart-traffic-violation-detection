"""Signal detection + red-light stop-line violation logic."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

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


def get_centroid(bbox: tuple[int, int, int, int]) -> Point:
    """Return centroid (x, y) from (x1, y1, x2, y2)."""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def check_line_crossing(
    prev_y: int,
    curr_y: int,
    line_y: int,
    buffer: int = 5,
    direction: str = "down",
) -> bool:
    """Line crossing with configurable direction: down, up, both."""
    direction = str(direction).strip().lower()
    crossed_down = prev_y < (line_y - buffer) and curr_y > (line_y + buffer)
    crossed_up = prev_y > (line_y + buffer) and curr_y < (line_y - buffer)
    if direction == "up":
        return crossed_up
    if direction == "both":
        return crossed_down or crossed_up
    return crossed_down


def detect_violation(
    track_id: int,
    history: list[Point],
    signal_state: str,
    line_y: int,
    buffer: int = 5,
    direction: str = "down",
) -> bool:
    """Spec-required helper: RED signal + line crossing from history."""
    _ = track_id
    if signal_state != "RED" or len(history) < 2:
        return False
    prev_y = history[-2][1]
    curr_y = history[-1][1]
    return check_line_crossing(prev_y, curr_y, line_y, buffer=buffer, direction=direction)


def get_signal_state(
    frame: np.ndarray,
    roi: tuple[int, int, int, int],
    red_ratio_threshold: float = 0.03,
) -> str:
    """HSV-based signal state from fixed ROI. Returns RED or GREEN."""
    x, y, w, h = roi
    frame_h, frame_w = frame.shape[:2]

    x = max(0, min(x, frame_w - 1))
    y = max(0, min(y, frame_h - 1))
    w = max(1, min(w, frame_w - x))
    h = max(1, min(h, frame_h - y))

    roi_frame = frame[y : y + h, x : x + w]
    if roi_frame.size == 0:
        return "GREEN"

    hsv = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)

    lower_red_1 = np.array([0, 120, 120], dtype=np.uint8)
    upper_red_1 = np.array([10, 255, 255], dtype=np.uint8)
    lower_red_2 = np.array([160, 120, 120], dtype=np.uint8)
    upper_red_2 = np.array([179, 255, 255], dtype=np.uint8)

    lower_green = np.array([35, 60, 60], dtype=np.uint8)
    upper_green = np.array([90, 255, 255], dtype=np.uint8)

    red_mask = cv2.inRange(hsv, lower_red_1, upper_red_1) | cv2.inRange(hsv, lower_red_2, upper_red_2)
    green_mask = cv2.inRange(hsv, lower_green, upper_green)

    total_pixels = float(w * h)
    red_ratio = float(np.count_nonzero(red_mask)) / max(1.0, total_pixels)
    green_ratio = float(np.count_nonzero(green_mask)) / max(1.0, total_pixels)

    if red_ratio >= red_ratio_threshold and red_ratio > (green_ratio * 1.1):
        return "RED"
    return "GREEN"


class RedLightViolationEngine:
    """Stateful red-light violation detector with evidence + JSON logging."""

    def __init__(self) -> None:
        self.track_history: dict[int, list[Point]] = defaultdict(list)
        self.track_line_y_history: dict[int, list[int]] = defaultdict(list)
        self.track_first_line_y: dict[int, int] = {}
        self.violated_ids: set[int] = set()
        self.pending_confirmations: dict[int, int] = {}
        self._history_size = 64

    def _is_stationary(self, history: list[Point], stationary_motion_px: int) -> bool:
        if len(history) < 3:
            return False
        p1 = np.array(history[-1], dtype=np.float32)
        p2 = np.array(history[-3], dtype=np.float32)
        motion = float(np.linalg.norm(p1 - p2))
        return motion < float(stationary_motion_px)

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
        frame: Optional[np.ndarray] = None,
        line_buffer: int = 5,
        crossing_direction: str = "down",
        crossing_point: str = "centroid",
        allow_start_below: bool = False,
        start_below_confirm_frames: int = 2,
        confirmation_frames: int = 2,
        stationary_motion_px: int = 3,
        save_evidence: bool = True,
        evidence_dir: str = "violations",
        json_log_path: str = "violations/violations.jsonl",
        plate_hook: Optional[Callable[[Any], Optional[str]]] = None,
    ) -> list[dict[str, Any]]:
        violations: list[dict[str, Any]] = []

        active_ids: set[int] = set()
        for obj in tracked_objects or []:
            track_id = int(getattr(obj, "track_id", -1))
            class_id = int(getattr(obj, "class_id", -1))
            class_name = str(getattr(obj, "class_name", _CLASS_ID_TO_NAME.get(class_id, "")))
            bbox = getattr(obj, "bbox", None)
            if track_id < 0 or class_name not in _ALLOWED_CLASSES or bbox is None or len(bbox) != 4:
                continue

            active_ids.add(track_id)
            centroid = get_centroid(tuple(map(int, bbox)))
            history = self.track_history[track_id]
            history.append(centroid)
            if len(history) > self._history_size:
                del history[:-self._history_size]

            # Crossing reference can be centroid or bottom edge of bbox.
            cross_y = int(bbox[3]) if str(crossing_point).strip().lower() == "bottom" else centroid[1]
            line_hist = self.track_line_y_history[track_id]
            line_hist.append(cross_y)
            if len(line_hist) > self._history_size:
                del line_hist[:-self._history_size]
            if track_id not in self.track_first_line_y:
                self.track_first_line_y[track_id] = cross_y

            if track_id in self.violated_ids:
                continue

            if self._is_stationary(history, stationary_motion_px=stationary_motion_px):
                self.pending_confirmations.pop(track_id, None)
                continue

            if detect_violation(
                track_id,
                [(0, y) for y in line_hist],
                signal_state,
                stop_line_y,
                buffer=line_buffer,
                direction=crossing_direction,
            ):
                self.pending_confirmations[track_id] = 1
                continue

            # Optional fallback for tracks that first appear already beyond line
            # (e.g., late detection/occlusion in crowded scenes).
            if allow_start_below and signal_state == "RED" and line_hist:
                first_y = self.track_first_line_y.get(track_id, line_hist[0])
                if first_y > (stop_line_y + line_buffer) and len(line_hist) >= max(1, int(start_below_confirm_frames)):
                    recent = line_hist[-max(1, int(start_below_confirm_frames)) :]
                    if all(y > (stop_line_y + line_buffer) for y in recent):
                        self.pending_confirmations[track_id] = max(
                            self.pending_confirmations.get(track_id, 0),
                            max(1, int(confirmation_frames)),
                        )

            if track_id not in self.pending_confirmations:
                continue

            curr_y = history[-1][1]
            if line_hist:
                curr_y = line_hist[-1]
            if signal_state == "RED" and curr_y > (stop_line_y + line_buffer):
                self.pending_confirmations[track_id] += 1
            else:
                self.pending_confirmations.pop(track_id, None)
                continue

            if self.pending_confirmations[track_id] < max(1, int(confirmation_frames)):
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
            if plate_hook is not None:
                payload["license_plate"] = plate_hook(obj)

            if save_evidence:
                self._append_json_log(json_log_path=json_log_path, payload=payload)

            self.violated_ids.add(track_id)
            self.pending_confirmations.pop(track_id, None)
            violations.append(payload)

        for stale_id in list(self.pending_confirmations.keys()):
            if stale_id not in active_ids:
                self.pending_confirmations.pop(stale_id, None)

        return violations


_ENGINE = RedLightViolationEngine()


def detect_signal_violation(
    tracked_objects: Iterable[Any],
    stop_line_y: int,
    signal_state: str,
    frame: Optional[np.ndarray] = None,
    line_buffer: int = 5,
    crossing_direction: str = "down",
        crossing_point: str = "centroid",
        allow_start_below: bool = False,
        start_below_confirm_frames: int = 2,
        confirmation_frames: int = 2,
    stationary_motion_px: int = 3,
    save_evidence: bool = True,
    evidence_dir: str = "violations",
    json_log_path: str = "violations/violations.jsonl",
    plate_hook: Optional[Callable[[Any], Optional[str]]] = None,
) -> list[dict[str, Any]]:
    """Backward-compatible wrapper around the stateful red-light engine."""
    return _ENGINE.update(
        tracked_objects=tracked_objects,
        stop_line_y=stop_line_y,
        signal_state=signal_state,
        frame=frame,
        line_buffer=line_buffer,
        crossing_direction=crossing_direction,
        crossing_point=crossing_point,
        allow_start_below=allow_start_below,
        start_below_confirm_frames=start_below_confirm_frames,
        confirmation_frames=confirmation_frames,
        stationary_motion_px=stationary_motion_px,
        save_evidence=save_evidence,
        evidence_dir=evidence_dir,
        json_log_path=json_log_path,
        plate_hook=plate_hook,
    )


def get_track_history() -> dict[int, list[Point]]:
    return dict(_ENGINE.track_history)


def get_violated_ids() -> set[int]:
    return set(_ENGINE.violated_ids)
