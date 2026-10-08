import os
import pandas as pd

yolo_labels_dir = "/Users/as-mac-1311/Downloads/Planogram/dataset_yolo/labels"
ideal_planograms_dir = "/Users/as-mac-1311/Downloads/Planogram/Dataset/ideal_planograms/csv"

ideal_planograms = {}
for i in range(1, 11):
    p_id = f"P{i:03d}"
    df = pd.read_csv(f"{ideal_planograms_dir}/{p_id}.csv")
    ideal_planograms[p_id] = df

results = []
for split in ["train", "val", "test"]:
    labels_path = os.path.join(yolo_labels_dir, split)
    if not os.path.exists(labels_path): continue
    for filename in os.listdir(labels_path):
        if not filename.endswith(".txt"): continue
        parts = filename.split("_")
        if len(parts) >= 2 and parts[1].startswith("P"):
            p_num = parts[1][1:]
            try:
                p_id = f"P{int(p_num):03d}"
            except:
                continue
            if p_id not in ideal_planograms: continue
            
            filepath = os.path.join(labels_path, filename)
            detected_skus = []
            with open(filepath, "r") as f:
                for line in f:
                    cls_id = int(line.split()[0])
                    sku_id = f"SKU_{cls_id + 1:03d}"
                    detected_skus.append(sku_id)
            
            ideal_df = ideal_planograms[p_id]
            expected_skus = ideal_df['sku_id'].tolist()
            
            # Simple matching simulation
            expected_counts = pd.Series(expected_skus).value_counts().to_dict()
            detected_counts = pd.Series(detected_skus).value_counts().to_dict()
            
            all_skus = set(expected_counts.keys()).union(set(detected_counts.keys()))
            
            total_missing = 0
            total_extra = 0
            matches = 0
            
            for sku in all_skus:
                exp = expected_counts.get(sku, 0)
                det = detected_counts.get(sku, 0)
                if det > exp:
                    total_extra += (det - exp)
                    matches += exp
                elif exp > det:
                    total_missing += (exp - det)
                    matches += det
                else:
                    matches += exp
            
            total_positions = len(expected_skus)
            
            # This is a rough estimation of compliance score (matches / total_positions)
            if total_positions > 0:
                score = matches / total_positions
            else:
                score = 0
                
            results.append({
                "Image": filename.replace(".txt", ".JPG"),
                "Planogram": p_id,
                "Detected Total": len(detected_skus),
                "Expected Total": total_positions,
                "Matches (SKU level)": matches,
                "Missing": total_missing,
                "Extra": total_extra,
                "Est. Score": f"{score*100:.1f}%"
            })

df = pd.DataFrame(results)
# Filter for interesting ones: score > 0 and score < 100
interesting = df[(df["Matches (SKU level)"] > 0) & (df["Missing"] > 0)]
print(interesting.sort_values("Matches (SKU level)", ascending=False).head(15).to_string(index=False))

