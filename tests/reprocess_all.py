from backend.app.core.database import SessionLocal
from backend.app.models import ShelfAudit
from backend.app.workers.pipeline import reprocess_audit_pipeline

db = SessionLocal()
audits = db.query(ShelfAudit).all()

for audit in audits:
    print(f"Reprocessing audit {audit.id}...")
    try:
        reprocess_audit_pipeline(audit.id)
        print(f"Success for {audit.id}")
    except Exception as e:
        print(f"Failed for {audit.id}: {e}")

print("All old audits reprocessed!")
