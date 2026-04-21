# TODO for detection-service: add retries, batching, and stronger validation for AI engine responses.
import base64
from pathlib import Path

import httpx

from config import settings
from schemas.detection import ViolationOut


async def run_detection(image_path: str, source: str = "upload") -> list[ViolationOut]:
    file_bytes = Path(image_path).read_bytes()
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    payload = {"image_base64": encoded, "source": source}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{settings.ai_engine_url}/run", json=payload)
        response.raise_for_status()

    data = response.json()
    violations = data.get("violations", [])
    return [ViolationOut(**violation) for violation in violations]
