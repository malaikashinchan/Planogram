"""
Celery tasks.
"""

from uuid import UUID

from backend.app.workers.celery_app import celery_app
from backend.app.workers.pipeline import process_audit_pipeline


@celery_app.task(bind=True, max_retries=3)
def process_audit_task(self, audit_id: str, job_id: str):
    """
    Background task to process an audit.
    """
    try:
        process_audit_pipeline(UUID(audit_id), UUID(job_id))
    except Exception as exc:
        # Retry for transient errors if needed
        # self.retry(exc=exc, countdown=60)
        raise exc

@celery_app.task(bind=True, max_retries=3)
def reprocess_audit_task(self, audit_id: str):
    """
    Background task to reconstruct the shelf and run compliance 
    after all HITL reviews are resolved.
    """
    from backend.app.workers.pipeline import reprocess_audit_pipeline
    try:
        reprocess_audit_pipeline(UUID(audit_id))
    except Exception as exc:
        raise exc

@celery_app.task
def cleanup_inactive_users_task():
    """
    Periodic task to hard-delete employees that have been INACTIVE for > 30 days.
    """
    import datetime
    from backend.app.core.database import SessionLocal
    from backend.app.models.user import User, UserStatus
    
    db = SessionLocal()
    try:
        thirty_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
        
        # In a real system, you'd add a 'status_updated_at' column, but for now we fallback to 'updated_at' 
        # or just delete any INACTIVE user who hasn't logged in recently and was created > 30 days ago.
        inactive_users = db.query(User).filter(
            User.status == UserStatus.INACTIVE,
            User.created_at < thirty_days_ago
        ).all()
        
        count = 0
        for u in inactive_users:
            # Optionally check if u.last_login_at < thirty_days_ago
            db.delete(u)
            count += 1
            
        db.commit()
        print(f"Cleaned up {count} inactive users.")
    except Exception as exc:
        db.rollback()
        print(f"Error cleaning up users: {exc}")
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=5)
def upload_to_s3_retry_task(self, local_file_path: str, storage_key: str, human_review_id: str = None, content_type: str = "image/jpeg"):
    """
    Background task that tries to upload a local file to S3 with exponential backoff + jitter.
    Once successful, it updates the database and deletes the local file.
    """
    import os
    import random
    from backend.app.services.storage_service import storage
    from backend.app.core.database import SessionLocal
    from backend.app.models.review import HumanReview, MLTrainingSample, StorageStatus
    
    if not os.path.exists(local_file_path):
        print(f"File {local_file_path} not found. Cannot upload to S3.")
        return
        
    db = SessionLocal()
    try:
        if human_review_id:
            # Mark attempt
            hr = db.query(HumanReview).filter(HumanReview.id == human_review_id).first()
            if hr:
                hr.storage_status = StorageStatus.FAILED_RETRYABLE
                db.commit()
                
        with open(local_file_path, "rb") as f:
            success = storage.upload(f, storage_key, content_type=content_type)
            
        if success:
            os.remove(local_file_path)
            print(f"Successfully uploaded {storage_key} to S3 and cleaned up local file.")
            if human_review_id:
                hr = db.query(HumanReview).filter(HumanReview.id == human_review_id).first()
                if hr:
                    hr.storage_status = StorageStatus.AVAILABLE
                    # Also update training sample if it was somehow created already
                    sample = db.query(MLTrainingSample).filter(MLTrainingSample.human_review_id == human_review_id).first()
                    if sample:
                        sample.storage_status = StorageStatus.AVAILABLE
                        sample.local_storage_path = None
                    hr.local_storage_path = None
                db.commit()
        else:
            raise Exception(f"storage.upload returned False for {storage_key}")
            
    except Exception as exc:
        db.rollback()
        # Exponential backoff with jitter: roughly 1m, 2m, 4m, 8m, 16m
        backoff_seconds = (2 ** self.request.retries) * 60
        jitter = random.randint(0, 30)
        retry_delay = backoff_seconds + jitter
        
        print(f"S3 Upload failed for {storage_key}, retrying in {retry_delay}s... ({exc})")
        raise self.retry(exc=exc, countdown=retry_delay)
    finally:
        db.close()
