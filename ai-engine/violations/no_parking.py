"""No-parking violation detection logic based on dwell time inside a zone."""

from __future__ import annotations

import time
from typing import Any, Iterable

# track_id -> first timestamp when the object entered the no-parking zone
entry_time: dict[int, float] = {}

_CLASS_ID_TO_NAME = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}
_ALLOWED_CLASSES = {"car", "motorcycle", "bus", "truck"}
_NO_PARKING_SECONDS = 5.0


def detect_no_parking(
    tracked_objects: Iterable[Any],
    zone: tuple[int, int, int, int],
) -> list[dict[str, Any]]:
    """
    Detect vehicles that remain inside a restricted zone for more than 5 seconds.

    Returns:
        [
            {"track_id": int, "type": "NO_PARKING"}
        ]
    """
    objects = list(tracked_objects or [])
    if not objects:
        entry_time.clear()
        return []

    zx1, zy1, zx2, zy2 = zone
    now = time.perf_counter()
    violations: list[dict[str, Any]] = []
    current_vehicle_track_ids: set[int] = set()

    for obj in objects:
        track_id = int(getattr(obj, "track_id", -1))
        if track_id < 0:
            continue

        class_id = int(getattr(obj, "class_id", -1))
        class_name = str(getattr(obj, "class_name", _CLASS_ID_TO_NAME.get(class_id, "")))
        if class_name not in _ALLOWED_CLASSES:
            continue

        bbox = getattr(obj, "bbox", None)
        if bbox is None or len(bbox) != 4:
            continue

        x1, y1, x2, y2 = map(int, bbox)
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        inside = zx1 < cx < zx2 and zy1 < cy < zy2
        current_vehicle_track_ids.add(track_id)

        if inside:
            if track_id not in entry_time:
                entry_time[track_id] = now
            else:
                duration = now - entry_time[track_id]
                if duration > _NO_PARKING_SECONDS:
                    violations.append({"track_id": track_id, "type": "NO_PARKING"})
        else:
            # Vehicle moved out of zone, so reset timer.
            entry_time.pop(track_id, None)

    # Cleanup stale tracks (vehicle disappeared from current frame).
    stale_ids = [tid for tid in entry_time if tid not in current_vehicle_track_ids]
    for tid in stale_ids:
        entry_time.pop(tid, None)

    return violations
