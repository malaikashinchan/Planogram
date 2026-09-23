from backend.app.ml.detection import run_yolo_detection

image_path = "Dataset/GroceryDataset_part1/ShelfImages/C1_P07_N1_S3_1.JPG"
with open(image_path, "rb") as f:
    image_bytes = f.read()

detections = run_yolo_detection(image_bytes)
print(f"Found {len(detections)} bounding boxes via bytes!")
if detections:
    print(f"Sample pipeline format: {detections[0]}")
