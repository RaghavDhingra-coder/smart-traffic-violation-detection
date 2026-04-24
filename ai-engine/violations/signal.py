"""Signal stop-line violation detection logic."""

from __future__ import annotations

from typing import Any, Iterable

crossed_ids: set[int] = set()
previous_positions: dict[int, int] = {}

_CLASS_ID_TO_NAME = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}
_ALLOWED_CLASSES = {"car", "motorcycle", "bus", "truck"}


def detect_signal_violation(
    tracked_objects: Iterable[Any],
    stop_line_y: int,
    signal_state: str,
) -> list[dict[str, Any]]:
    """Detect tracks that cross stop line while signal is RED."""
    violations: list[dict[str, Any]] = []

    if signal_state != "RED":
        return []

    for obj in tracked_objects or []:
        track_id = int(getattr(obj, "track_id", -1))
        class_id = int(getattr(obj, "class_id", -1))
        class_name = str(getattr(obj, "class_name", _CLASS_ID_TO_NAME.get(class_id, "")))
        if class_name not in _ALLOWED_CLASSES:
            continue

        bbox = getattr(obj, "bbox", None)
        if bbox is None or len(bbox) != 4:
            continue

        _, y1, _, y2 = bbox
        cy = (int(y1) + int(y2)) // 2
        prev_cy = previous_positions.get(track_id)

        # Store current position for crossing check in the next frame.
        previous_positions[track_id] = cy

        if prev_cy is None:
            continue

        if prev_cy < stop_line_y and cy >= stop_line_y and track_id not in crossed_ids:
            crossed_ids.add(track_id)
            violations.append({"track_id": track_id, "type": "SIGNAL_VIOLATION"})

    return violations
