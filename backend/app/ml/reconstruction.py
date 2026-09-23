import numpy as np
from sklearn.cluster import DBSCAN
import logging

logger = logging.getLogger(__name__)

from backend.app.core.config import settings

def reconstruct_shelf(detections: list[dict], recognitions: list[dict]) -> list[dict]:
    """
    Takes raw YOLO detections and ResNet recognitions and reconstructs the logical shelf.
    Uses DBSCAN on Y-coordinates to find shelves, then sorts X-coordinates for positions.

    Returns a list of shelves, each containing a list of products:
    [
        {
            "shelf_id": 1,
            "products": [
                {
                    "position": 1,
                    "sku_id": "SKU_001",
                    "confidence": 0.95
                }, ...
            ]
        }, ...
    ]
    """
    if not detections or not recognitions:
        return []

    boxes = []
    # Combine detections and recognitions
    for rec in recognitions:
        det_idx = rec["detection_index"]
        det = detections[det_idx]
        
        x1, y1, x2, y2 = det["bbox"]
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        height = det["height"]
        
        boxes.append({
            "center_x": center_x,
            "center_y": center_y,
            "height": height,
            "sku_id": rec["predicted_sku_id"],
            "confidence": det["confidence"],  # Or a combined metric
            "recognition_similarity": rec["similarity"],
            "recognition_margin": rec["margin"]
        })

    # Dynamic DBSCAN clustering based on average bounding box height
    avg_height = np.mean([b["height"] for b in boxes])
    y_coords = np.array([[b["center_y"]] for b in boxes])
    
    clustering = DBSCAN(eps=avg_height * settings.YOLO_CLUSTER_EPS_RATIO, min_samples=1).fit(y_coords)
    
    # Group boxes into clusters
    clusters = {}
    for box, label in zip(boxes, clustering.labels_):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(box)
        
    # Order clusters top-to-bottom (min mean center_y first)
    cluster_means = []
    for label, c_boxes in clusters.items():
        mean_y = np.mean([b["center_y"] for b in c_boxes])
        cluster_means.append((label, mean_y, c_boxes))
        
    cluster_means.sort(key=lambda x: x[1])  # Sort ASC by Y (Top is y=0)
    
    shelves_output = []
    
    # Build logical schema
    for shelf_idx, (label, mean_y, c_boxes) in enumerate(cluster_means, start=1):
        # Sort boxes left-to-right
        c_boxes.sort(key=lambda b: b["center_x"])
        
        products_output = []
        for pos_idx, b in enumerate(c_boxes, start=1):
            products_output.append({
                "position": pos_idx,
                "sku_id": b["sku_id"],
                "confidence": b["confidence"],
                "recognition_similarity": b["recognition_similarity"],
                "recognition_margin": b["recognition_margin"]
            })
            
        shelves_output.append({
            "shelf_id": shelf_idx,
            "products": products_output
        })
        
    logger.info(f"Reconstructed {len(shelves_output)} shelves with {len(boxes)} total products.")
    return shelves_output
