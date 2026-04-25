"""DeepSORT tracker module for Phase 2 object tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from deep_sort_realtime.deepsort_tracker import DeepSort

from detector import Detection


@dataclass(frozen=True)
class TrackedObject:
    """Represents a tracked detection with a stable track ID."""

    track_id: int
    class_id: int
    confidence: float
    bbox: tuple[int, int, int, int]


class ObjectTracker:
    """Wrapper around DeepSORT for tracking YOLO detections across frames."""

    def __init__(
        self,
        max_age: int = 30,
        n_init: int = 2,
        max_iou_distance: float = 0.7,
        use_appearance: bool = False,
    ) -> None:
        self.use_appearance = use_appearance
        self.tracker = DeepSort(
            max_age=max_age,
            n_init=n_init,
            max_iou_distance=max_iou_distance,
            embedder="mobilenet" if use_appearance else None,
        )

    def update(self, detections: List[Detection], frame: np.ndarray) -> List[TrackedObject]:
        """Update tracker state from YOLO detections and return confirmed tracks."""
        frame_h, frame_w = frame.shape[:2]

        # Optimization 5: avoid tracker update call when no detections are available.
        if not detections:
            return []

        # DeepSORT expects detections as: ([x, y, w, h], confidence, class_id)
        ds_detections = []
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            w = max(0, x2 - x1)
            h = max(0, y2 - y1)
            if w == 0 or h == 0:
                continue
            ds_detections.append(([x1, y1, w, h], float(det.confidence), int(det.class_id)))

        if not ds_detections:
            return []

        tracker_kwargs = {"frame": frame} if self.use_appearance else {"embeds": self._build_fast_embeddings(ds_detections)}
        tracks = self.tracker.update_tracks(ds_detections, **tracker_kwargs)

        tracked_objects: List[TrackedObject] = []
        for track in tracks:
            if not track.is_confirmed():
                continue

            ltrb = track.to_ltrb()
            if ltrb is None:
                continue

            x1, y1, x2, y2 = map(int, ltrb)
            x1 = max(0, min(x1, frame_w - 1))
            y1 = max(0, min(y1, frame_h - 1))
            x2 = max(0, min(x2, frame_w - 1))
            y2 = max(0, min(y2, frame_h - 1))

            if x2 <= x1 or y2 <= y1:
                continue

            det_class = track.get_det_class()
            class_id = int(det_class) if det_class is not None else -1
            det_conf = track.get_det_conf()
            confidence = float(det_conf) if det_conf is not None else 0.0

            tracked_objects.append(
                TrackedObject(
                    track_id=int(track.track_id),
                    class_id=class_id,
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2),
                )
            )

        return tracked_objects

    @staticmethod
    def _build_fast_embeddings(ds_detections: list[tuple[list[float], float, int]]) -> np.ndarray:
        """
        Build lightweight deterministic embeddings for no-appearance mode.

        Newer deep-sort-realtime versions require either an embedder or explicit
        embeddings. These features keep fast IoU-style behavior without loading a
        heavy re-ID model.
        """
        if not ds_detections:
            return np.zeros((0, 8), dtype=np.float32)

        embeds: list[np.ndarray] = []
        for (x, y, w, h), conf, class_id in ds_detections:
            cx = x + (w * 0.5)
            cy = y + (h * 0.5)
            vec = np.array(
                [
                    float(cx),
                    float(cy),
                    float(w),
                    float(h),
                    float(conf),
                    float(class_id),
                    float(w * h),
                    float((w + h) * 0.5),
                ],
                dtype=np.float32,
            )
            norm = float(np.linalg.norm(vec))
            if norm > 1e-8:
                vec = vec / norm
            else:
                vec = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
            embeds.append(vec)

        return np.vstack(embeds).astype(np.float32)


_DEFAULT_TRACKER: Optional[ObjectTracker] = None


def track_objects(detections: List[Detection]) -> List[TrackedObject]:
    """
    Required helper: track detections and return tracked objects.

    Uses a lightweight synthetic frame bounds when caller does not provide a frame.
    """
    global _DEFAULT_TRACKER
    if _DEFAULT_TRACKER is None:
        _DEFAULT_TRACKER = ObjectTracker(use_appearance=False)

    if not detections:
        return []

    max_x = max(det.bbox[2] for det in detections) + 8
    max_y = max(det.bbox[3] for det in detections) + 8
    frame = np.zeros((max(16, max_y), max(16, max_x), 3), dtype=np.uint8)
    return _DEFAULT_TRACKER.update(detections, frame)
