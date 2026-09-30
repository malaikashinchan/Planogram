import uuid
from backend.app.workers.pipeline import reprocess_audit_pipeline

audit_id = uuid.UUID("0c7fe404-233a-4b2e-bc40-f54cb40014c9")
print(f"Reprocessing audit {audit_id}...")
reprocess_audit_pipeline(audit_id)
print("Done!")
