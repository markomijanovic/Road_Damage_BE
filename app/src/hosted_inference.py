"""Optional Roboflow hosted inference with the local model's response interface."""
import base64
import cv2
import requests


class HostedModel:
    def __init__(self, model_id, api_key):
        self.model_id = model_id
        self.api_key = api_key
        self.session = requests.Session()
        self.frames = 0
        self.detections = 0

    def infer(self, frame, verbose=False, confidence=0.1, iou_threshold=0.5):
        encoded, image = cv2.imencode(".jpg", frame)
        if not encoded:
            raise ValueError("Cannot encode inference frame")
        # Never include the request URL or credentials in exceptions/logs.
        try:
            response = self.session.post(
                f"https://detect.roboflow.com/{self.model_id}",
                params={"api_key": self.api_key, "confidence": confidence * 100,
                        "overlap": iou_threshold * 100},
                data=base64.b64encode(image.tobytes()),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=90,
            )
        except requests.RequestException:
            raise RuntimeError("Roboflow inference request failed") from None
        if response.status_code != 200:
            raise RuntimeError(f"Roboflow inference returned HTTP {response.status_code}")
        result = response.json()
        if "predictions" not in result:
            raise RuntimeError("Roboflow returned no predictions field")
        self.frames += 1
        self.detections += len(result["predictions"])
        if self.frames % 30 == 0:
            print(f"Processed {self.frames} frames; {self.detections} raw detections", flush=True)
        return [result]
