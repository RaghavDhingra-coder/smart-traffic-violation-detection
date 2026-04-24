"""Basic no-helmet violation detection logic (placeholder)."""

from __future__ import annotations

from typing import Any, Iterable

PERSON_CLASS_ID = 0
BIKE_CLASS_IDS = {1, 3}


def _intersection_area(b1: tuple[int, int, int, int], b2: tuple[int, int, int, int]) -> int:
    """Return intersection area between two boxes in xyxy format."""
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])
    if x2 <= x1 or y2 <= y1:
        return 0
    return (x2 - x1) * (y2 - y1)


def detect_no_helmet(tracked_objects: Iterable[Any]) -> list[dict[str, Any]]:
    """
    Placeholder no-helmet detection.

    For each motorcycle with at least one overlapping person, flag NO_HELMET.
    """
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
