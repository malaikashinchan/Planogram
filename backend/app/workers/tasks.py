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
