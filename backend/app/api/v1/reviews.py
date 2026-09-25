from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.auth.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.models.review import HumanReview, ReviewStatus, MLTrainingSample, SampleStatus
from backend.app.models.ml import Recognition, RecognitionStatus
from backend.app.models.audit import ShelfAudit
from backend.app.services.storage_service import storage
from backend.app.workers.celery_app import celery_app

router = APIRouter()

class ReviewResponse(BaseModel):
    id: UUID
    audit_id: UUID
    predicted_product_id: Optional[UUID]
    predicted_similarity: Optional[float]
    crop_url: str

class ResolveReviewRequest(BaseModel):
    corrected_product_id: Optional[UUID] = None
    is_new_product: bool = False
    new_product_name: Optional[str] = None
    new_product_brand: Optional[str] = None
    new_product_category: Optional[str] = None

@router.get("/pending", response_model=List[ReviewResponse])
def get_pending_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    reviews = db.query(HumanReview).filter(
        HumanReview.organization_id == current_user.organization_id,
        HumanReview.status == ReviewStatus.PENDING
    ).all()
    
    result = []
    for r in reviews:
        crop_url = storage.generate_url(r.crop_storage_key) if r.crop_storage_key else ""
        result.append(ReviewResponse(
            id=r.id,
            audit_id=r.audit_id,
            predicted_product_id=r.predicted_product_id,
            predicted_similarity=r.predicted_similarity,
            crop_url=crop_url
        ))
    return result

@router.post("/{review_id}/resolve")
def resolve_review(
    review_id: UUID,
    req: ResolveReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from datetime import datetime, timezone
    from backend.app.models.product import Product, ProductImage
    
    review = db.query(HumanReview).filter(
        HumanReview.id == review_id,
        HumanReview.organization_id == current_user.organization_id,
        HumanReview.status == ReviewStatus.PENDING
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Pending review not found")
        
    final_product_id = req.corrected_product_id
    
    # 0. Handle New Product Creation
    if req.is_new_product:
        if not req.new_product_name:
            raise HTTPException(status_code=400, detail="Product name is required for new products")
            
        all_skus = db.query(Product.sku_code).filter(
            Product.organization_id == current_user.organization_id,
            Product.sku_code.like("SKU_%")
        ).all()
        
        max_num = 0
        for (sku,) in all_skus:
            try:
                num = int(sku.split("_")[1])
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
                
        new_sku_code = f"SKU_{max_num + 1:03d}"
        
        new_prod = Product(
            organization_id=current_user.organization_id,
            sku_code=new_sku_code,
            name=req.new_product_name,
            brand=req.new_product_brand,
            category=req.new_product_category
        )
        db.add(new_prod)
        db.flush()
        
        final_product_id = new_prod.id
        
        # Save the crop as the first product image so training works
        if review.crop_storage_key:
            new_img = ProductImage(
                product_id=new_prod.id,
                storage_key=review.crop_storage_key,
                image_type="front"
            )
            db.add(new_img)
            
    elif not final_product_id:
        raise HTTPException(status_code=400, detail="corrected_product_id is required if not a new product")
        
    # 1. Complete HumanReview
    review.corrected_product_id = final_product_id
    review.status = ReviewStatus.COMPLETED
    review.reviewer_id = current_user.id
    review.reviewed_at = datetime.now(timezone.utc)
    
    # 2. Update Recognition
    rec = db.query(Recognition).filter(Recognition.id == review.recognition_id).first()
    if rec:
        rec.predicted_product_id = final_product_id
        rec.status = RecognitionStatus.HUMAN_CORRECTED
        
    # 3. Create MLTrainingSample
    sample = MLTrainingSample(
        organization_id=review.organization_id,
        crop_storage_key=review.crop_storage_key,
        correct_product_id=final_product_id,
        human_review_id=review.id,
        status=SampleStatus.PENDING
    )
    db.add(sample)
    db.commit()
    
    # 4. Deterministic Reprocessing Check
    pending_audit_reviews = db.query(HumanReview).filter(
        HumanReview.audit_id == review.audit_id,
        HumanReview.status == ReviewStatus.PENDING
    ).count()
    
    if pending_audit_reviews == 0:
        # Send task to reconstruct shelf and run compliance
        celery_app.send_task("backend.app.workers.tasks.reprocess_audit_task", args=[str(review.audit_id)])
        
    # 5. Automatic Retraining Trigger Check
    pending_samples = db.query(MLTrainingSample).filter(
        MLTrainingSample.status == SampleStatus.PENDING
    ).count()
    
    if pending_samples >= settings.MIN_NEW_TRAINING_SAMPLES:
        celery_app.send_task("backend.app.workers.training_tasks.launch_training_task")
        
    return {"status": "success", "message": "Review resolved"}
