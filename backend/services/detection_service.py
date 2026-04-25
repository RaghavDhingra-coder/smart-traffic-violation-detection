import httpx

try:
    from ..config import settings
    from ..schemas.detection import DetectionItem
except ImportError:
    from config import settings
    from schemas.detection import DetectionItem


class DetectionServiceError(Exception):
    pass


class DetectionUpstreamError(DetectionServiceError):
    pass


class DetectionResponseError(DetectionServiceError):
    pass


async def run_detection(image_base64: str, source: str = "webcam") -> list[DetectionItem]:
    payload = {"image_base64": image_base64, "source": source}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{settings.ai_engine_url}/run", json=payload)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise DetectionUpstreamError("AI detection service timed out") from exc
    except httpx.HTTPStatusError as exc:
        details = exc.response.text.strip()
        suffix = f": {details}" if details else ""
        raise DetectionUpstreamError(
            f"AI detection service returned status {exc.response.status_code}{suffix}"
        ) from exc
    except httpx.HTTPError as exc:
        raise DetectionUpstreamError("Failed to reach AI detection service") from exc

    try:
        body = response.json()
    except ValueError as exc:
        raise DetectionResponseError("AI detection service returned invalid JSON") from exc

    detections = body.get("detections", [])
    if not isinstance(detections, list):
        raise DetectionResponseError("AI detection response has invalid detections payload")

    try:
        return [DetectionItem(**item) for item in detections]
    except Exception as exc:  # noqa: BLE001
        raise DetectionResponseError(f"AI detection response validation failed: {exc}") from exc
