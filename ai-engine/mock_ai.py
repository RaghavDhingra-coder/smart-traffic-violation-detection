from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class RunReq(BaseModel):
    image_base64: str
    source: str = "webcam"

@app.post("/run")
def run(_: RunReq):
    return {
        "detections": [
            {"track_id": 3, "plate": "KA01AB1234", "type": "OVERSPEEDING"}
        ]
    }
