import json
from backend.app.ml.detection import run_yolo_detection
from backend.app.ml.recognition import run_recognition
from backend.app.ml.reconstruction import reconstruct_shelf

image_path = "Dataset/GroceryDataset_part1/ShelfImages/C1_P07_N1_S3_1.JPG"
with open(image_path, "rb") as f:
    image_bytes = f.read()

print("Running YOLO Detection...")
detections = run_yolo_detection(image_bytes)

print("Running ResNet50 Recognition...")
recognitions = run_recognition(image_bytes, detections)

print("Running DBSCAN Reconstruction...")
shelves = reconstruct_shelf(detections, recognitions)

for shelf in shelves:
    print(f"\nShelf {shelf['shelf_id']}:")
    for prod in shelf['products']:
        print(f"  Pos {prod['position']}: {prod['sku_id']} (Conf: {prod['confidence']:.2f}, Sim: {prod['recognition_similarity']:.2f})")

print("\n✅ Reconstruction Test Complete!")
