"""Utility helpers for drawing detections and FPS overlay."""

from __future__ import annotations

from typing import Iterable, Mapping, Protocol

import cv2
import numpy as np

# Stable colors for better readability in live streams.
CLASS_COLORS = {
    "person": (80, 220, 80),
    "car": (255, 178, 50),
    "motorcycle": (70, 140, 255),
}


class DrawableDetection(Protocol):
    """Common structure for both raw detections and tracked detections."""

    bbox: tuple[int, int, int, int]
    class_id: int
    confidence: float


def _get_class_name(
    detection: DrawableDetection,
    class_names: Mapping[int, str] | None,
) -> str:
    if class_names is not None:
        return class_names.get(detection.class_id, str(detection.class_id))
    return str(detection.class_id)


def draw_detections(
    frame: np.ndarray,
    detections: Iterable[DrawableDetection],
    class_names: Mapping[int, str] | None = None,
    min_confidence: float = 0.5,
) -> np.ndarray:
    """Draw bounding boxes and labels in-place and return the frame."""
    for detection in detections:
        # Optimization 6: skip low-confidence tracks to keep visualization clean.
        if detection.confidence <= min_confidence:
            continue

        x1, y1, x2, y2 = detection.bbox
        class_name = _get_class_name(detection, class_names)
        color = CLASS_COLORS.get(class_name, (255, 255, 255))

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        track_id = getattr(detection, "track_id", None)
        if track_id is not None:
            plate_text = getattr(detection, "plate", None)
            if plate_text is None:
                # Backward compatibility with older annotated objects.
                plate_text = getattr(detection, "plate_text", None)
            label = f"{class_name} ID:{track_id}"
            if plate_text:
                label += f" {plate_text}"

            violation_text = getattr(detection, "violation", None)
            if violation_text:
                label += f" [{violation_text}]"
        else:
            label = f"{class_name} {detection.confidence:.2f}"

        text_y = max(20, y1 - 8)
        cv2.putText(
            frame,
            label,
            (x1, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )

    return frame


def draw_fps(frame: np.ndarray, fps: float) -> np.ndarray:
    """Render FPS counter on the frame."""
    cv2.putText(
        frame,
        f"FPS: {fps:.2f}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (20, 20, 255),
        2,
        cv2.LINE_AA,
    )
    return frame
