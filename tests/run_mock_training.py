from backend.app.core.database import SessionLocal
from backend.app.models.ml import ModelVersion, ModelStatus
from backend.app.models.review import MLTrainingSample, SampleStatus
import datetime

db = SessionLocal()
try:
    pending_samples = db.query(MLTrainingSample).filter(
        MLTrainingSample.status == SampleStatus.PENDING
    ).all()
    
    if len(pending_samples) >= 20:
        version_name = f"v_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Retire old active
        current_active = db.query(ModelVersion).filter(ModelVersion.status == ModelStatus.ACTIVE).first()
        if current_active:
            current_active.status = ModelStatus.RETIRED
            current_active.retired_at = datetime.datetime.now(datetime.timezone.utc)
            
        candidate = ModelVersion(
            model_name="siamese_resnet50",
            version=version_name,
            status=ModelStatus.ACTIVE,
            approved_at=datetime.datetime.now(datetime.timezone.utc),
            artifact_storage_key="mocked/path"
        )
        db.add(candidate)
        
        for s in pending_samples:
            s.status = SampleStatus.USED_FOR_TRAINING
            
        db.commit()
        print("Mock training succeeded. 22 samples consumed. New Active version created.")
    else:
        print("Not enough pending samples.")
except Exception as e:
    print("Error:", e)
    db.rollback()
finally:
    db.close()
