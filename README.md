# Retail Planogram Compliance System

An end-to-end computer vision pipeline for automated retail shelf monitoring, planogram compliance, and SKU recognition. 

This project mathematically extracts bounding boxes, identifies product SKUs using contrastive retrieval, reconstructs 2D shelf structures, and compares the physical shelf against an ideal JSON planogram.

## 🚀 System Architecture

```text
                    RETAILER INPUT
                         │
              ┌──────────┴──────────┐
              │                     │
        Shelf Image            Ideal Planogram
              │                 CSV/Excel/JSON
              ↓                   
   ┌────────────────────┐
   │ 1. YOLOv8 Detector │  ← Locates all products on shelf
   └────────┬───────────┘
            │
            ↓
   ┌────────────────────┐
   │ 2. SKU Identifier  │  ← Siamese ResNet50 + Triplet Loss
   └────────┬───────────┘
            │
            ↓
   ┌────────────────────┐
   │ 3. Shelf Engine    │  ← Reconstructs 2D logical layout
   └────────┬───────────┘
            │
            ↓
    [Actual Planogram]  ────────→  [Comparison Engine]  ← Outputs Compliance Score
```

---

## 📈 Project Status & Roadmap

- ✅ **Phase 1-5**: Dataset preparation, YOLOv8 baseline training & evaluation.
- ✅ **Phase 6A-6L**: Brand Retrieval Engine (Frozen Baseline vs. Disjoint Fine-tuning).
- 🔄 **Phase 6M-6N**: Target-Domain Metric Learning (Triplet Margin Loss). *(In Progress)*
- 🔜 **Phase 7**: Shelf Reconstruction (2D logical mapping).
- 🔜 **Phase 8-16**: Planogram Comparison, PostgreSQL, FastAPI, React Dashboard.

---

## 🔬 Walkthrough & Results Archive

### Phase 1–5: YOLOv8 Object Detection

**Approach:** 
We converted the raw `GroceryDataset` annotations into normalized YOLO format. To establish a baseline, we trained YOLOv8 (nano) for 100 epochs to detect a single class (`product`).

**Results:**
- **mAP50**: 94.3%
- **mAP50-95**: 70.8%
- **Precision**: 91.5%
- **Recall**: 89.2%

The detector is highly capable of finding densely packed cigarette packs on retail shelves, despite heavy occlusion and varied lighting.

**YOLOv8 Performance Visualizations:**
![YOLOv8 PR Curve](outputs/evaluation/test_metrics/BoxPR_curve.png)
![YOLOv8 Confusion Matrix](outputs/evaluation/test_metrics/confusion_matrix_normalized.png)

### Phase 6: Brand / SKU Identification (Retrieval)

**Approach:** 
Instead of training a standard classifier (which requires retraining whenever a new SKU is added), we built an **Embedding Retrieval Engine**. We extract 2048-d embeddings for shelf crops and compare them against a reference catalogue using Cosine Similarity.

#### Baseline 1: Frozen ImageNet Features (Phase 6H)
Using a completely frozen `ResNet50_Weights.IMAGENET1K_V2` backbone without any domain adaptation:
- **Top-1 Accuracy**: 49.09%
- **Top-5 Accuracy**: 64.10%
- *Analysis*: Generic visual features (shapes, red colors) overlap heavily. The model struggled severely to distinguish *Marlboro* (21% accuracy) from *Pall Mall* because it couldn't read logos or specific brand packaging textures.

**Frozen Baseline Visualizations:**
![Frozen Retrieval Evaluation](outputs/retrieval/retrieval_evaluation.png)

#### Baseline 2: Disjoint Fine-Tuning (Phase 6J-6K)
We fine-tuned Layers 3 & 4 of ResNet50 on a 2000-class subset of the `Products-10K` dataset.
- **Top-1 Accuracy**: 49.34%
- **Top-5 Accuracy**: 57.73%
- *Analysis (Domain Shift)*: The model learned highly discriminative features (boosting Pall Mall accuracy by +42% and Marlboro by +20%). However, because `Products-10K` (Chinese drinks/snacks) is completely disjoint from `GroceryDataset` (European cigarettes), the model lost its generic generalization abilities, causing Top-5 accuracy to crash.

**Fine-Tuned Prototype Visualizations:**
![Fine-Tuned Similarity](outputs/retrieval_finetuned/finetuned_similarity.png)
![Fine-Tuned Accuracy](outputs/retrieval_finetuned/finetuned_accuracy.png)

#### Baseline 3: Target-Domain Metric Learning (Phase 6M-6N)
Instead of standard cross-entropy, we optimized the embedding space directly using **Triplet Margin Loss** on the GroceryDataset shelf crops (Anchors), true catalogue images (Positives), and incorrect catalogue images (Negatives).
- **Top-1 Accuracy**: 100.0% (In-domain)
- **Top-5 Accuracy**: 100.0% (In-domain)
- *Analysis*: By explicitly enforcing $d(Anchor, Positive) < d(Anchor, Negative)$, the model perfectly separated the 10 target SKUs in the 2048-d space. While this is an in-domain score, it definitively proves the retrieval architecture succeeds when given target-domain supervision.

**Target-Domain Visualizations:**
![Metric Similarity](outputs/retrieval_metric/metric_similarity.png)
![Metric Accuracy](outputs/retrieval_metric/metric_accuracy.png)

---

## Phase 7: Shelf Reconstruction & Planogram Engine

We translated the pure machine learning outputs (bounding boxes + feature vectors) into structured, SKU-agnostic business logic. 

**Core Pipeline:**
1. **Parsers (7B-7C):** Ingests raw retailer mock planograms in `.json`, `.csv`, `.xls`, and `.xlsx` formats, instantly normalizing them into a rigid **Canonical JSON** format.
2. **Validator (7D):** Enforces data integrity. Will immediately halt the pipeline if it detects Duplicate Positions, Missing Positions, Unknown SKUs, or Shelf Overflows in the Canonical Planogram.
3. **Shelf Reconstruction (7E):** Converts raw physical YOLO crops into a logical layout. Dynamically clusters `center_y` (DBSCAN) to detect shelf rows without hardcoding counts, and sorts `center_x` to assign logical Position indices. Outputs `actual_shelf.json`.
4. **Comparison Engine (7F):** Performs 3-tier validation (Shelf Existence, Product Inventory, Spatial Arrangement) between the Actual and Ideal planograms to generate deterministic Raw Compliance Metrics and actionable JSON violations (Missing, Misplaced, Extra, Facing deltas).

---

## 🗄️ System Memory & Database Architecture (Upcoming)

To make the system truly adaptable and "future-proof", we are implementing a PostgreSQL layer that operates on three memory tiers:

1. **Product Memory**: 
   Stores SKU metadata and pre-computed reference embeddings (`VECTOR(2048)`). When a new product is added, the manager simply uploads a reference image; it is embedded and immediately becomes searchable without retraining the neural network.
2. **Audit Memory**:
   Stores shelf audits, YOLO detections, and the confidence margin of the ResNet50 retrieval engine.
3. **Learning Memory (Human-in-the-Loop)**:
   If the retrieval engine returns a *low confidence* margin, the crop is sent for **Human Review**. The manager corrects the predicted SKU. This accumulated correction data is routinely used to retrain the Embedding Model, continuously bridging the domain gap for new and difficult SKUs.

---

## 🛠️ Technology Stack

- **Machine Learning**: PyTorch, Torchvision, Ultralytics (YOLOv8), OpenCV.
- **Data Engineering**: Pandas, NumPy.
- **Infrastructure (Upcoming)**: FastAPI, PostgreSQL, React, TailwindCSS.
