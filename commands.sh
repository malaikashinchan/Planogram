#!/bin/bash
# Planogram Compliance System - Execution Commands
# This file maintains a sequential record of how to run the pipeline from scratch.

# 1. Activate Virtual Environment
source venv/bin/activate

# 2. Phase 2: Annotation Visualization
python ML-Models/phase2_annotation_viz.py

# 3. Phase 3: Convert annotations to YOLO format
python ML-Models/convert_to_yolo.py

# 4. Phase 4: Train YOLO baseline
python ML-Models/phase4_train_yolo.py

# 5. Phase 5: Evaluate YOLO test evaluation
python ML-Models/phase5_evaluate.py

# 6. Phase 6A/6B: Catalogue Audit
python ML-Models/phase6b5_catalogue_audit.py

# 7. Phase 6C: Generate YOLO Product Crops
python ML-Models/phase6c_generate_crops.py

# 8. Phase 6D/6E: Extract Embeddings (ResNet50 Frozen)
python ML-Models/phase6de_embeddings.py

# 9. Phase 6F-6H: Similarity Retrieval & Evaluation (ImageNet Baseline)
python ML-Models/phase6fgh_retrieval.py

# 10. Phase 6I: Fine-Grained Dataset Audit (Products-10K/RPC)
python ML-Models/phase6i_dataset_audit.py

# 11. Phase 6J: Products-10K Prototype Fine-Tuning
python ML-Models/phase6ja_finetune.py

# 12. Phase 6K: Re-evaluate on GroceryDataset (Fine-Tuned Baseline)
python ML-Models/phase6k_reevaluate.py

# 13. Phase 6M: Target-Domain Metric Learning (Triplet Loss)
python ML-Models/phase6m_metric_learning.py

# 14. Phase 6N: Re-evaluate on GroceryDataset (Metric Learning Baseline)
python ML-Models/phase6n_reevaluate_metric.py

# 15. Phase 7: Shelf Reconstruction & Planogram Engine
python Shelf_Reconstruction/phase7a_product_master.py
python Shelf_Reconstruction/phase7b_ideal_planograms.py
python Shelf_Reconstruction/phase7c_parsers.py
python Shelf_Reconstruction/phase7d_validator.py
python Shelf_Reconstruction/phase7e_reconstruction.py
python Shelf_Reconstruction/phase7f_comparison.py

# 16. Phase 7G: End-to-End Experiment B (ML vs Ground Truth)
python Shelf_Reconstruction/phase7g_experiment_b.py

# =========================================================
# Phase 8: PostgreSQL Database & Backend
# =========================================================
python -c "from pydantic_settings import BaseSettings; print('PYDANTIC SETTINGS OK')"

docker-compose up -d

source venv/bin/activate

cd backend

python -c "from backend.app.core.config import settings; print(settings.DATABASE_URL)"
python -c "from backend.app.models import *; print('MODEL IMPORT OK')"

alembic current

alembic revision --autogenerate -m "Init Schema Phase 8"

# INSPECT GENERATED MIGRATION

alembic upgrade head

# CREATE INITIAL ORGANIZATION

# cd ..

# export SEED_ORGANIZATION_ID="<REAL-ORGANIZATION-UUID>"

# python backend/scripts/seed_phase7.py
