from backend.app.core.database import SessionLocal
from backend.app.models import ComplianceViolation
import uuid

audit_id = uuid.UUID("0c7fe404-233a-4b2e-bc40-f54cb40014c9")
db = SessionLocal()
violations = db.query(ComplianceViolation).filter(ComplianceViolation.audit_id == audit_id).all()
for v in violations:
    print(v.violation_type, v.shelf_id, v.position)
