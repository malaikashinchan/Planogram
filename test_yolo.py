from backend.app.ml.detection import ProductDetector

detector = ProductDetector("runs/grocery_baseline/weights/best.pt")
image_path = "Dataset/GroceryDataset_part1/ShelfImages/C1_P07_N1_S3_1.JPG"
detections = detector.detect(image_path, conf_threshold=0.25)
print(f"Found {len(detections)} bounding boxes!")
if detections:
    print(f"Sample: {detections[0]}")
