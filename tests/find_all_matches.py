import cv2
import glob
from pathlib import Path
from backend.app.ml.detection import ProductDetector
from backend.app.ml.recognition import ProductRecognizer
from backend.app.ml.reconstruction import reconstruct_shelf
from backend.app.ml.compliance import calculate_compliance
from backend.app.core.config import settings

def load_planogram(csv_path):
    import pandas as pd
    df = pd.read_csv(csv_path)
    return df.to_dict('records')

def main():
    detector = ProductDetector(settings.YOLO_MODEL_PATH)
    recognizer = ProductRecognizer(
        settings.RESNET_MODEL_PATH,
        settings.REFERENCE_EMBEDDINGS_PATH,
        settings.REFERENCE_LABELS_PATH
    )
    
    planograms = {}
    for p_path in sorted(glob.glob("./Dataset/ideal_planograms/csv/P0*.csv")):
        name = Path(p_path).stem
        planograms[name] = load_planogram(p_path)
        
    # Gather images (try plain ShelfImages first, take a sample if too many, but let's use annotated_shelves since they have guaranteed products)
    images = glob.glob("./Dataset/annotated_shelves/*.jpg")
    
    # Store matches: { planogram_name: [list of matching images] }
    matches = {name: [] for name in planograms.keys()}
    
    print(f"Scanning {len(images)} images against {len(planograms)} planograms...")
    
    for idx, img_path in enumerate(images):
        img = cv2.imread(img_path)
        if img is None: continue
        detections = detector.detect(img)
        if not detections: continue
        recognitions = recognizer.recognize(img, detections)
        if not recognitions: continue
        shelf_data = reconstruct_shelf(detections, recognitions)
        
        for p_name, p_data in planograms.items():
            # Only need to find a few matches per planogram to save output space
            if len(matches[p_name]) >= 3:
                continue
                
            report = calculate_compliance(shelf_data, p_data)
            score = report["position_accuracy"] + report["availability_rate"] + report["facing_compliance"]
            if score > 0:
                matches[p_name].append(Path(img_path).name)
                
        # Stop early if all planograms have at least 3 matches
        if all(len(m) >= 3 for m in matches.values()):
            print(f"Found matches for all planograms after checking {idx+1} images.")
            break

    print("\n--- NON-ZERO SCORE IMAGES FOR EACH PLANOGRAM ---")
    for p_name in sorted(matches.keys()):
        imgs = matches[p_name]
        if not imgs:
            print(f"[{p_name}]: No images found that give > 0 score in the sample.")
        else:
            print(f"[{p_name}]:")
            for img in imgs:
                print(f"  - {img}")

if __name__ == "__main__":
    main()
