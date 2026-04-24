"""YOLO-based license plate detector for cropped vehicle images."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

# Keep Ultralytics cache/config within project to avoid user-profile permission issues.
_PROJECT_DIR = Path(__file__).resolve().parent
_ULTRALYTICS_DIR = _PROJECT_DIR / ".ultralytics"
_ULTRALYTICS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(_ULTRALYTICS_DIR))

from ultralytics import YOLO

DEFAULT_PLATE_MODEL_PATH = "models/plate/best.pt"


class PlateDetector:
    """Detect and crop the best license plate region from a vehicle image."""

    def __init__(
        self,
        model_path: str = DEFAULT_PLATE_MODEL_PATH,
        conf_threshold: float = 0.10,
    ) -> None:
        self.conf_threshold = conf_threshold
        self.model = None
        self.is_available = False

        project_dir = Path(__file__).resolve().parent
        resolved_model_path = project_dir / model_path
        self.model_path = resolved_model_path

        if not resolved_model_path.exists():
            print(f"Warning: Plate model not found at '{resolved_model_path}'. Plate YOLO will be skipped.")
            return

        try:
            self.model = YOLO(str(resolved_model_path))
            self.is_available = True
        except Exception:  # noqa: BLE001
            print(f"Warning: Failed to load plate model from '{resolved_model_path}'. Plate YOLO will be skipped.")
            self.model = None
            self.is_available = False

    def detect_plate(self, vehicle_img: np.ndarray) -> Optional[np.ndarray]:
        """
        Run plate detection on a vehicle crop and return the best plate crop.

        Returns None when no plate is detected or input is invalid.
        """
        if self.model is None:
            return self._fallback_detect_plate(vehicle_img)
        if vehicle_img is None or vehicle_img.size == 0:
            return None

        try:
            results = self.model(vehicle_img, conf=self.conf_threshold, verbose=False)
        except Exception:  # noqa: BLE001
            return None

        if not results:
            return self._fallback_detect_plate(vehicle_img)

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return self._fallback_detect_plate(vehicle_img)

        h, w = vehicle_img.shape[:2]
        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()

        # Prefer highest-confidence box that also looks plate-like.
        sorted_idx = np.argsort(-confs)
        best_candidate: Optional[tuple[int, int, int, int]] = None
        best_score = -1.0

        for idx in sorted_idx:
            x1, y1, x2, y2 = xyxy[int(idx)].astype(int).tolist()
            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(0, min(x2, w - 1))
            y2 = max(0, min(y2, h - 1))

            if x2 <= x1 or y2 <= y1:
                continue
            if not self._is_reasonable_plate_box(x1, y1, x2, y2, w, h):
                continue

            bw = x2 - x1
            bh = y2 - y1
            center_y = (y1 + y2) / 2.0
            # Prefer lower and wider boxes with decent confidence.
            score = (
                float(confs[int(idx)]) * 2.0
                + (center_y / max(1.0, float(h))) * 1.2
                + (bw / max(1.0, float(w))) * 0.8
                - (bh / max(1.0, float(h))) * 0.3
            )
            if score > best_score:
                best_score = score
                best_candidate = (x1, y1, x2, y2)

        if best_candidate is not None:
            x1, y1, x2, y2 = best_candidate
            plate_crop = vehicle_img[y1:y2, x1:x2]
            if plate_crop.size > 0:
                return plate_crop

        return self._fallback_detect_plate(vehicle_img)

    @staticmethod
    def _is_reasonable_plate_box(
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        image_w: int,
        image_h: int,
    ) -> bool:
        """Reject obvious false positives from YOLO plate detector."""
        bw = max(0, x2 - x1)
        bh = max(1, y2 - y1)
        area = bw * bh
        area_ratio = area / float(max(1, image_w * image_h))
        aspect = bw / float(bh)
        center_y = (y1 + y2) / 2.0
        width_ratio = bw / float(max(1, image_w))
        height_ratio = bh / float(max(1, image_h))

        if not (2.2 <= aspect <= 8.5):
            return False
        if not (0.006 <= area_ratio <= 0.30):
            return False
        if not (0.18 <= width_ratio <= 0.95):
            return False
        if not (0.05 <= height_ratio <= 0.45):
            return False
        # Plates are usually not in the top half of a vehicle crop.
        if center_y < image_h * 0.45:
            return False
        return True

    def _fallback_detect_plate(self, vehicle_img: np.ndarray) -> Optional[np.ndarray]:
        """
        Classical fallback when YOLO plate model is unavailable.

        Uses edge + contour filtering to find a likely plate-like rectangle.
        """
        if vehicle_img is None or vehicle_img.size == 0:
            return None

        h, w = vehicle_img.shape[:2]
        if h < 40 or w < 80:
            return None

        try:
            gray = cv2.cvtColor(vehicle_img, cv2.COLOR_BGR2GRAY)
            gray = cv2.bilateralFilter(gray, 9, 75, 75)
            edges = cv2.Canny(gray, 100, 200)

            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return None

            best_score = -1.0
            best_rect: Optional[tuple[int, int, int, int]] = None
            image_area = float(h * w)

            for cnt in contours:
                x, y, cw, ch = cv2.boundingRect(cnt)
                if cw <= 0 or ch <= 0:
                    continue

                area = cw * ch
                area_ratio = area / image_area
                aspect = cw / max(ch, 1)

                # Plate heuristics:
                # - wide rectangle
                # - medium area relative to vehicle crop
                # - likely in lower half of vehicle
                if not (2.0 <= aspect <= 6.5):
                    continue
                if not (0.01 <= area_ratio <= 0.35):
                    continue
                if y < int(h * 0.35):
                    continue

                score = aspect * 0.4 + area_ratio * 4.0 + (y / h) * 0.6
                if score > best_score:
                    best_score = score
                    best_rect = (x, y, cw, ch)

            if best_rect is None:
                return None

            x, y, cw, ch = best_rect
            pad_x = int(cw * 0.08)
            pad_y = int(ch * 0.20)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(w, x + cw + pad_x)
            y2 = min(h, y + ch + pad_y)

            if x2 <= x1 or y2 <= y1:
                return None

            plate_crop = vehicle_img[y1:y2, x1:x2]
            if plate_crop.size == 0:
                return None
            return plate_crop
        except Exception:  # noqa: BLE001
            return None
