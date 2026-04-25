"""Simple per-track speed estimator based on center-point displacement."""

from __future__ import annotations

import math
import time
from typing import Any, Iterable

# Private globals — never accessed directly by callers.
_prev_positions: dict[int, tuple[int, int]] = {}
_prev_times: dict[int, float] = {}
_speed_map: dict[int, float] = {}

_CLASS_ID_TO_NAME = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}
_ALLOWED_CLASSES = {"car", "motorcycle", "bus", "truck"}

# --------------------------------------------------------------------------- #
# Tuning constants — adjust to your camera setup.                              #
# --------------------------------------------------------------------------- #
# Minimum elapsed time between two samples before computing speed.
# Prevents noise-division when frames arrive very rapidly.
MIN_DT_SECONDS: float = 0.05

# Discard speed samples above this threshold — they are almost certainly
# caused by the tracker swapping IDs or a bbox teleport artifact.
MAX_PLAUSIBLE_SPEED_PX_S: float = 1500.0

# Optional: convert px/s → km/h for display.
# Measure a real object of known length in your scene and set accordingly.
# e.g. if a 4-metre car spans 80 px → PIXELS_PER_METER = 20.
PIXELS_PER_METER: float = 20.0
METERS_PER_SECOND_TO_KMH: float = 3.6


def pixels_per_second_to_kmh(px_s: float) -> float:
    """Convert raw pixel speed to km/h using PIXELS_PER_METER calibration."""
    return (px_s / PIXELS_PER_METER) * METERS_PER_SECOND_TO_KMH


def estimate_speed(
    tracked_objects: Iterable[Any],
    active_track_ids: set[int] | None = None,
) -> dict[int, float]:
    """
    Estimate per-track speed in pixels/second using consecutive center positions.

    Parameters
    ----------
    tracked_objects:
        Iterable of tracker output objects.  Each must expose `track_id`,
        `class_id`, and `bbox` attributes.
    active_track_ids:
        Set of track IDs that are alive in the *current* frame.  When provided,
        dead tracks are pruned from all internal caches so stale speed values
        never leak into future frames.

    Returns
    -------
    dict mapping track_id → speed in pixels/second **for the current frame
    only**.  Tracks with insufficient history (first appearance) are omitted.
    """
    current_time = time.time()
    current_frame_speeds: dict[int, float] = {}

    for obj in tracked_objects or []:
        track_id = int(getattr(obj, "track_id", -1))
        if track_id < 0:
            continue

        class_id = int(getattr(obj, "class_id", -1))
        class_name = str(
            getattr(obj, "class_name", _CLASS_ID_TO_NAME.get(class_id, ""))
        )

        # Skip non-vehicle classes when class_id is confidently known.
        if class_id >= 0 and class_name not in _ALLOWED_CLASSES:
            continue

        bbox = getattr(obj, "bbox", None)
        if bbox is None or len(bbox) != 4:
            continue

        x1, y1, x2, y2 = bbox
        cx = (int(x1) + int(x2)) // 2
        cy = (int(y1) + int(y2)) // 2

        if track_id in _prev_positions and track_id in _prev_times:
            prev_x, prev_y = _prev_positions[track_id]
            dt = current_time - _prev_times[track_id]

            if dt >= MIN_DT_SECONDS:
                dist = math.sqrt((cx - prev_x) ** 2 + (cy - prev_y) ** 2)
                speed = dist / dt

                if speed <= MAX_PLAUSIBLE_SPEED_PX_S:
                    _speed_map[track_id] = speed
                    current_frame_speeds[track_id] = speed

                # Always advance position after a valid dt window.
                _prev_positions[track_id] = (cx, cy)
                _prev_times[track_id] = current_time
            # If dt < MIN_DT_SECONDS, keep previous position until enough time passes.
        else:
            # First sighting of this track — record baseline, no speed yet.
            _prev_positions[track_id] = (cx, cy)
            _prev_times[track_id] = current_time

    # ---------------------------------------------------------------------- #
    # Prune stale tracks so dead vehicles don't ghost in speed_map forever.   #
    # ---------------------------------------------------------------------- #
    if active_track_ids is not None:
        dead_ids = set(_speed_map.keys()) - active_track_ids
        for tid in dead_ids:
            _speed_map.pop(tid, None)
            _prev_positions.pop(tid, None)
            _prev_times.pop(tid, None)

    # Return ONLY speeds computed this frame, never historical leftovers.
    return current_frame_speeds


def reset() -> None:
    """Clear all internal state.  Useful for unit tests or source switching."""
    _prev_positions.clear()
    _prev_times.clear()
    _speed_map.clear()