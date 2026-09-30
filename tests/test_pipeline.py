import cv2
from backend.app.ml.detection import ProductDetector
from backend.app.ml.recognition import ProductRecognizer
from backend.app.ml.reconstruction import reconstruct_shelf
from backend.app.core.config import settings

def main():
    detector = ProductDetector(settings.YOLO_MODEL_PATH)
    recognizer = ProductRecognizer(
        settings.RESNET_MODEL_PATH,
        settings.REFERENCE_EMBEDDINGS_PATH,
        settings.REFERENCE_LABELS_PATH
    )
    
    img_path = "./Dataset/GroceryDataset_part1/ShelfImages/C1_P01_N1_S3_1.JPG"
    print(f"Running pipeline on {img_path}...")
    img = cv2.imread(img_path)
    
    detections = detector.detect(img)
    print(f"Found {len(detections)} boxes.")
    
    recognitions = recognizer.recognize(img, detections)
    print(f"Recognized {len(recognitions)} products.")
    
    shelf_data = reconstruct_shelf(detections, recognitions)
    for shelf in shelf_data:
        print(f"Shelf {shelf['shelf_id']}:")
        for p in shelf['products']:
            print(f"  Pos {p['position']}: {p['sku_id']} ({p.get('confidence', 0):.2f})")

if __name__ == "__main__":
    main()
