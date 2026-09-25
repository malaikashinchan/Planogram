from backend.app.services.storage_service import storage
from backend.app.core.database import SessionLocal
from backend.app.models import AuditImage, ShelfAudit

db = SessionLocal()
latest_audit = db.query(ShelfAudit).order_by(ShelfAudit.created_at.desc()).first()
audit_img = db.query(AuditImage).filter(AuditImage.audit_id == latest_audit.id).first()

if audit_img and audit_img.storage_key:
    file_bytes = storage.download(audit_img.storage_key)
    with open('test_image.jpg', 'wb') as f:
        f.write(file_bytes)
    print("Downloaded image to test_image.jpg")
else:
    print("No image found.")
