# TODO for plate-ocr: improve plate localization, multilingual OCR, and post-processing rules for Indian plates.
import re

import easyocr
import numpy as np


class PlateOCR:
    def __init__(self) -> None:
        # STUB: replace with real implementation by tuning OCR models and language packs for deployment.
        self.reader = easyocr.Reader(["en"], gpu=False)

    def extract_plate(self, cropped_image: np.ndarray) -> str:
        if cropped_image.size == 0:
            return "UNKNOWN"

        # STUB: replace with real implementation using preprocessing and confidence filtering.
        result = self.reader.readtext(cropped_image, detail=0)
        if not result:
            return "UNKNOWN"
        return self.clean_plate(" ".join(result))

    def clean_plate(self, raw_text: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_text or "")
        return cleaned.upper() or "UNKNOWN"
