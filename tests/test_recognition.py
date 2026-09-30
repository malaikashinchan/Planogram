import json
from backend.app.ml.detection import run_yolo_detection
from backend.app.ml.recognition import run_recognition

image_path = "Dataset/GroceryDataset_part1/ShelfImages/C1_P07_N1_S3_1.JPG"
with open(image_path, "rb") as f:
    image_bytes = f.read()

print("Running YOLO Detection...")
detections = run_yolo_detection(image_bytes)
print(f"Found {len(detections)} bounding boxes.")

print("\nRunning ResNet50 Recognition...")
recognitions = run_recognition(image_bytes, detections)

for idx, rec in enumerate(recognitions):
    det = detections[rec["detection_index"]]
    print(f"\nDetection {idx + 1}:")
    print(f"  class_id: {det['class_id']}")
    print(f"  confidence: {det['confidence']:.4f}")
    print(f"  predicted_sku: {rec['predicted_sku_id']} (Category {rec['category_id']})")
    print(f"  similarity: {rec['similarity']:.4f}")
    print(f"  margin: {rec['margin']:.4f}")

print("\n✅ Test Complete!")
