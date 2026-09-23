import logging
import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO
import sys

logger = logging.getLogger(__name__)

class ProductDetector:
    def __init__(self, model_path: str | Path):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"YOLO weights not found at: {self.model_path}")
        
        logger.info(f"Loading YOLO model from {self.model_path}")
        self.model = YOLO(str(self.model_path))

    def detect(self, image_data, conf_threshold: float = 0.25) -> list[dict]:
        """
        Runs YOLO object detection on the provided image (bytes, path, or cv2 numpy array).
        Returns a list of detections: [{"bbox": [x1, y1, x2, y2], "confidence": float, "class_id": int}]
        """
        # If image_data is bytes, decode it
        if isinstance(image_data, bytes):
            np_arr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image bytes.")
        else:
            img = image_data

        results = self.model(img, conf=conf_threshold, verbose=False)
        
        detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                
                # Convert to width/height for pipeline
                width = x2 - x1
                height = y2 - y1
                
                detections.append({
                    "bbox": [x1, y1, x2, y2],
                    "x": x1,
                    "y": y1,
                    "width": width,
                    "height": height,
                    "confidence": conf,
                    "class_id": cls
                })
                
        logger.info(f"YOLO found {len(detections)} products.")
        return detections


# ── Global Singleton for Celery Worker ──
# This ensures the model is loaded only once when the worker imports this module.

try:
    from backend.app.core.config import settings
    _detector_instance = ProductDetector(settings.YOLO_MODEL_PATH)
except Exception as e:
    logger.error(f"Failed to load YOLO model: {e}")
    # Don't crash the whole import if running outside Celery (e.g. tests)
    _detector_instance = None


def run_yolo_detection(image_bytes: bytes) -> list[dict]:
    """
    Entry point for the ML pipeline. Uses the singleton detector.
    """
    if not _detector_instance:
        raise RuntimeError("YOLO detector was not initialized successfully.")
    
    return _detector_instance.detect(image_bytes)
