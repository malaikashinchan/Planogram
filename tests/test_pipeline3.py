import cv2
import glob
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
    
    images = glob.glob("./Dataset/annotated_shelves/*.jpg")
    for img_path in images[:10]:
        print(f"\n--- {img_path} ---")
        img = cv2.imread(img_path)
        if img is None:
            continue
        detections = detector.detect(img)
        print(f"Found {len(detections)} boxes.")
        if detections:
            recognitions = recognizer.recognize(img, detections)
            shelf_data = reconstruct_shelf(detections, recognitions)
            for shelf in shelf_data:
                print(f"Shelf {shelf['shelf_id']}:")
                for p in shelf['products']:
                    print(f"  Pos {p['position']}: {p['sku_id']} ({p.get('confidence', 0):.2f})")

if __name__ == "__main__":
    main()
