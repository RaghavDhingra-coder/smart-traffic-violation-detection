"""Simple per-track speed estimator based on center-point displacement."""

from __future__ import annotations

import math
import time
from typing import Any, Iterable

prev_positions: dict[int, tuple[int, int]] = {}
prev_times: dict[int, float] = {}
speed_map: dict[int, float] = {}

_CLASS_ID_TO_NAME = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}
_ALLOWED_CLASSES = {"car", "motorcycle", "bus", "truck"}


def estimate_speed(tracked_objects: Iterable[Any]) -> dict[int, float]:
    """Estimate per-track speed in pixels/second using consecutive positions."""
    for obj in tracked_objects or []:
        track_id = int(getattr(obj, "track_id", -1))
        class_id = int(getattr(obj, "class_id", -1))
        class_name = str(getattr(obj, "class_name", _CLASS_ID_TO_NAME.get(class_id, "")))
        if track_id < 0 or class_name not in _ALLOWED_CLASSES:
            continue

        bbox = getattr(obj, "bbox", None)
        if bbox is None or len(bbox) != 4:
            continue

        x1, y1, x2, y2 = bbox
        cx = (int(x1) + int(x2)) // 2
        cy = (int(y1) + int(y2)) // 2
        current_time = time.time()

        if track_id in prev_positions and track_id in prev_times:
            prev_x, prev_y = prev_positions[track_id]
            dt = current_time - prev_times[track_id]
            if dt > 0:
                dist = math.sqrt((cx - prev_x) ** 2 + (cy - prev_y) ** 2)
                speed_map[track_id] = dist / dt

        prev_positions[track_id] = (cx, cy)
        prev_times[track_id] = current_time

    return speed_map

