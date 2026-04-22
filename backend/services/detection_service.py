# TODO for detection-service: add retries, batching, and stronger validation for AI engine responses.
import asyncio
import base64
from pathlib import Path
from typing import Optional

import httpx

try:
    from ..config import settings
    from ..schemas.detection import ViolationOut
    from ..schemas.violation import ViolationCreate
    from .violation_service import insert_violation
except ImportError:
    from config import settings
    from schemas.detection import ViolationOut
    from schemas.violation import ViolationCreate
    from services.violation_service import insert_violation


class DetectionServiceError(Exception):
    pass


class DetectionUpstreamError(DetectionServiceError):
    pass


class DetectionResponseError(DetectionServiceError):
    pass


async def run_detection(image_path: str, source: str = "upload") -> list[ViolationOut]:
    file_bytes = await asyncio.to_thread(Path(image_path).read_bytes)
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    payload = {"image_base64": encoded, "source": source}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{settings.ai_engine_url}/run", json=payload)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise DetectionUpstreamError("AI detection service timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise DetectionUpstreamError(
            f"AI detection service returned status {exc.response.status_code}"
        ) from exc
    except httpx.HTTPError as exc:
        raise DetectionUpstreamError("Failed to reach AI detection service") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise DetectionResponseError("AI detection service returned invalid JSON") from exc

    violations = data.get("violations", [])
    if not isinstance(violations, list):
        raise DetectionResponseError("AI detection response has invalid violations payload")

    return [ViolationOut(**violation) for violation in violations]


async def store_detected_violations(
    violations: list[ViolationOut],
    location: Optional[str] = None,
) -> None:
    violation_payloads = []
    for violation in violations:
        payload = ViolationCreate.from_detection(violation, location=location)
        if payload is not None:
            violation_payloads.append(payload)

    await asyncio.gather(
        *(asyncio.to_thread(insert_violation, payload) for payload in violation_payloads)
    )
