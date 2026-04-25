"""Triple riding violation detection logic."""

from __future__ import annotations

from typing import Any, Iterable

PERSON_CLASS_ID = 0
BIKE_CLASS_IDS = {1, 3}
_BIKE_TOP_EXPAND_RATIO = 0.50


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
    """
    Expand motorcycle bbox upward to include rider torso/head region.

    YOLO often predicts bike boxes low around wheels/body, while person boxes
    sit higher. Using only raw box overlap undercounts pillion riders.
    """
    x1, y1, x2, y2 = mbox
    h = max(1, y2 - y1)
    top_expand = int(h * _BIKE_TOP_EXPAND_RATIO)
    return (x1, max(0, y1 - top_expand), x2, y2)


def _is_rider_associated(
    person_box: tuple[int, int, int, int],
    bike_box: tuple[int, int, int, int],
) -> bool:
    """
    Robustly link person to motorcycle.

    Accept match when:
    1) person overlaps expanded rider region, or
    2) person's bottom-center point lies inside expanded rider region.
    """
    rider_region = _expanded_rider_region(bike_box)
    if _intersection_area(person_box, rider_region) > 0:
        return True

    px = (person_box[0] + person_box[2]) // 2
    py = person_box[3]
    rx1, ry1, rx2, ry2 = rider_region
    return rx1 <= px <= rx2 and ry1 <= py <= ry2


def detect_triple_riding(tracked_objects: Iterable[Any]) -> list[dict[str, Any]]:
    """
    Detect motorcycles with 3 or more overlapping persons.

    Returns:
        [
            {"track_id": int, "type": "TRIPLE_RIDING", "count": int}
        ]
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

        overlap_count = 0
        for person in persons:
            pbox = getattr(person, "bbox", None)
            if pbox is None:
                continue
            if _is_rider_associated(pbox, mbox):
                overlap_count += 1

        if overlap_count >= 3:
            violations.append(
                {
                    "track_id": int(getattr(motorcycle, "track_id", -1)),
                    "type": "TRIPLE_RIDING",
                    "count": overlap_count,
                }
            )
            break

    return violations
