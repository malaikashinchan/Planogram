import cv2
import glob
import json
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
    for p_path in glob.glob("./Dataset/ideal_planograms/csv/*.csv"):
        name = Path(p_path).stem
        planograms[name] = load_planogram(p_path)
        
    images = glob.glob("./Dataset/annotated_shelves/*.jpg")[:50] # Just test first 50
    
    best_combos = []
    
    for img_path in images:
        img = cv2.imread(img_path)
        if img is None: continue
        detections = detector.detect(img)
        if not detections: continue
        recognitions = recognizer.recognize(img, detections)
        if not recognitions: continue
        shelf_data = reconstruct_shelf(detections, recognitions)
        
        for p_name, p_data in planograms.items():
            report = calculate_compliance(shelf_data, p_data)
            score = report["position_accuracy"] + report["availability_rate"] + report["facing_compliance"]
            if score > 0:
                best_combos.append({
                    "planogram": p_name,
                    "image": Path(img_path).name,
                    "pos_acc": report["position_accuracy"],
                    "avail": report["availability_rate"],
                    "facing": report["facing_compliance"],
                    "score": score
                })
                
    best_combos.sort(key=lambda x: x["score"], reverse=True)
    print("\n--- BEST MATCHES ---")
    for combo in best_combos[:10]:
        print(f"Planogram: {combo['planogram']}, Image: {combo['image']}")
        print(f"  Pos Acc: {combo['pos_acc']:.0%}, Avail: {combo['avail']:.0%}, Facing: {combo['facing']:.0%}")

if __name__ == "__main__":
    main()
