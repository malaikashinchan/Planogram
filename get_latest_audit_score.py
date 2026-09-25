from backend.app.core.database import SessionLocal
from backend.app.models import ShelfAudit, ComplianceResult, Detection, ComplianceViolation

db = SessionLocal()
latest_audit = db.query(ShelfAudit).order_by(ShelfAudit.created_at.desc()).first()

if latest_audit:
    print(f"Latest Audit ID: {latest_audit.id}")
    print(f"Created At: {latest_audit.created_at}")
    
    detections = db.query(Detection).filter_by(audit_id=latest_audit.id).count()
    print(f"\nTotal YOLO Detections: {detections}")
    
    comp = db.query(ComplianceResult).filter_by(audit_id=latest_audit.id).first()
    if comp:
        print("\nCompliance Scores:")
        print(f"- Overall Compliance (Availability Rate): {comp.availability_rate * 100}%")
        print(f"- Position Accuracy: {comp.position_accuracy * 100}%")
        print(f"- Facing Compliance: {comp.facing_compliance * 100}%")
    else:
        print("No compliance results found yet (might still be processing).")
        
    violations = db.query(ComplianceViolation).filter_by(audit_id=latest_audit.id).count()
    print(f"\nTotal Violations Recorded: {violations}")
else:
    print("No audits found.")
