# Machine Learning Lifecycle & Human-in-the-Loop

Our platform uses a robust, self-improving ML architecture.

## 1. Object Detection (YOLO)
When an image is uploaded, YOLO detects bounding boxes for all products on the shelf. If no products are detected, the audit is marked as `NEEDS_RETAKE`.

## 2. Product Recognition (ResNet)
Each detected crop is passed through a ResNet Embedding Net, which converts the image into a mathematical vector. This vector is compared against the Reference Embeddings of your Product Master using Cosine Similarity.

## 3. Human Review
If the top similarity score is below the `RECOGNITION_REVIEW_THRESHOLD` (usually 0.40), the system flags the product for Human Review. The audit pauses and waits for a Manager to manually resolve the crop via the "Reviews" tab.

## 4. Retraining (Outbox Pattern)
When a manager resolves a review, the crop is saved locally and asynchronously uploaded to AWS S3. 
Once successfully uploaded, the sample's `storage_status` becomes `AVAILABLE`.
When the number of `AVAILABLE` samples reaches the `MIN_NEW_TRAINING_SAMPLES` threshold (usually 20), a background Celery task automatically fine-tunes the ResNet model using Triplet Margin Loss.

## 5. Model Promotion
The newly trained model is evaluated against a fixed holdout dataset. If the evaluation loss shows no regression compared to the current baseline, the new model is promoted to `ACTIVE` status and will be used for all future audits!
