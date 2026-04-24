"""OCR helpers for vehicle number plate extraction."""

from __future__ import annotations

import re
from typing import Optional

import cv2
import easyocr
import numpy as np

_reader: easyocr.Reader | None = None
_INDIAN_PLATE_CORE = re.compile(r"[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}")


def _get_reader() -> easyocr.Reader:
    """Lazy-initialize EasyOCR once for better runtime performance."""
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def clean_text(raw_text: str) -> str:
    """Normalize OCR output by removing non-alphanumeric noise."""
    if not raw_text:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", raw_text).upper()


def is_plausible_plate(text: str) -> bool:
    """Basic sanity check for Indian-style plate text."""
    if not text:
        return False
    if not (8 <= len(text) <= 12):
        return False
    has_letter = any(ch.isalpha() for ch in text)
    has_digit = any(ch.isdigit() for ch in text)
    return has_letter and has_digit


def normalize_plate_text(text: str) -> str:
    """
    Canonicalize OCR output to reduce noisy leading/trailing characters.

    Example: XHR26DO5551 -> HR26DO5551
    """
    cleaned = clean_text(text)
    if not cleaned:
        return ""

    # Prefer a plate-like core substring if present.
    match = _INDIAN_PLATE_CORE.search(cleaned)
    if match:
        return match.group(0)

    # Fallback: trim one noisy leading char when it creates a plausible candidate.
    if len(cleaned) >= 9:
        trimmed = cleaned[1:]
        if is_plausible_plate(trimmed):
            return trimmed

    return cleaned


def preprocess_plate_image(image: np.ndarray) -> Optional[np.ndarray]:
    """Preprocess crop to improve OCR quality on small/noisy plates."""
    if image is None or image.size == 0:
        return None

    try:
        # 1) Grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # 2) Upscale 2x for better character resolution
        upscaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        # 3) Binary threshold for clearer foreground/background separation
        _, thresh = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh
    except Exception:  # noqa: BLE001
        return None


def _candidate_variants(image: np.ndarray) -> list[np.ndarray]:
    """Build multiple OCR candidates to improve robustness on varied lighting."""
    variants: list[np.ndarray] = []
    # Include original crop first; EasyOCR often performs better on natural RGB plates.
    variants.append(image)

    processed = preprocess_plate_image(image)
    if processed is not None and processed.size > 0:
        variants.append(processed)

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        upscaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)

        # CLAHE helps when plate contrast is poor.
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        clahe_img = clahe.apply(upscaled)
        variants.append(clahe_img)

        # Inverted threshold can work for dark backgrounds / compression artifacts.
        _, inv_thresh = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        variants.append(inv_thresh)

        # Mild denoise + threshold candidate.
        denoised = cv2.GaussianBlur(upscaled, (3, 3), 0)
        _, denoise_thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(denoise_thresh)
    except Exception:  # noqa: BLE001
        pass

    # Remove empty entries defensively.
    return [v for v in variants if v is not None and v.size > 0]


def extract_text(image: np.ndarray) -> Optional[str]:
    """
    Run OCR on a cropped plate image and return cleaned plate text.

    Returns None when OCR fails or text is too noisy.
    """
    if image is None or image.size == 0:
        return None

    try:
        reader = _get_reader()
        candidates = _candidate_variants(image)
        if not candidates:
            return None

        # Prefer strong plate charset to reduce OCR noise.
        allowlist = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        best_text = ""
        best_score = -1

        for candidate in candidates:
            # detail=0 returns only text strings.
            results = reader.readtext(candidate, detail=0, allowlist=allowlist, paragraph=False)
            if not results:
                continue

            tokens = [clean_text(str(text)) for text in results if text is not None]
            tokens = [t for t in tokens if t]
            if not tokens:
                continue

            candidate_texts = set(tokens)
            candidate_texts.add("".join(tokens))

            for text in candidate_texts:
                normalized = normalize_plate_text(text)
                if is_plausible_plate(normalized):
                    return normalized

                score = len(normalized)
                if any(ch.isalpha() for ch in normalized) and any(ch.isdigit() for ch in normalized):
                    score += 2
                if len(normalized) < 6:
                    score -= 6

                if score > best_score:
                    best_score = score
                    best_text = normalized
    except Exception:  # noqa: BLE001
        return None

    if not best_text:
        return None
    if not is_plausible_plate(best_text):
        return None
    return best_text


# Backward-compatible alias for existing imports.
def extract_plate_text(image: np.ndarray) -> Optional[str]:
    return extract_text(image)


def crop_plate_from_vehicle(frame: np.ndarray, bbox: tuple[int, int, int, int]) -> Optional[np.ndarray]:
    """
    Crop a likely plate region from the lower-center area of a vehicle box.

    This is a simple heuristic and can be upgraded later with a plate detector.
    """
    if frame is None or frame.size == 0:
        return None

    frame_h, frame_w = frame.shape[:2]
    x1, y1, x2, y2 = bbox

    x1 = max(0, min(x1, frame_w - 1))
    y1 = max(0, min(y1, frame_h - 1))
    x2 = max(0, min(x2, frame_w - 1))
    y2 = max(0, min(y2, frame_h - 1))

    if x2 <= x1 or y2 <= y1:
        return None

    # Crop only the detected vehicle first.
    vehicle = frame[y1:y2, x1:x2]
    if vehicle.size == 0:
        return None

    # Focus region:
    # - Bottom 40% of vehicle height
    # - Center 60% of vehicle width
    h, w = vehicle.shape[:2]
    plate_y1 = int(h * 0.6)
    plate_y2 = h
    plate_x1 = int(w * 0.2)
    plate_x2 = int(w * 0.8)

    if plate_x2 <= plate_x1 or plate_y2 <= plate_y1:
        return None

    plate_crop = vehicle[plate_y1:plate_y2, plate_x1:plate_x2]
    if plate_crop.size == 0:
        return None
    return plate_crop
