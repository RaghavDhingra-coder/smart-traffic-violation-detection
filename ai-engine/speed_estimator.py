# TODO for speed-estimation: replace the mock return value with calibrated tracking, perspective correction, and DeepSORT integration.
import random


class SpeedEstimator:
    def estimate(self, frame, prev_frame, fps: int = 30) -> float:
        # STUB: replace with real implementation because accurate speed requires camera calibration and stable multi-object tracking such as DeepSORT.
        return round(random.uniform(40.0, 120.0), 2)
