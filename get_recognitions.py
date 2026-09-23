import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from backend.app.core.database import SessionLocal
from backend.app.models.ml import Detection, Recognition
from backend.app.models.product import Product

db = SessionLocal()
audit_id = "502fc140-d2c9-4b40-b1f7-15734f74c148"

recognitions = db.query(Recognition, Product, Detection).join(
    Detection, Recognition.detection_id == Detection.id
).outerjoin(
    Product, Recognition.predicted_product_id == Product.id
).filter(
    Detection.audit_id == audit_id
).all()

print(f"--- Recognitions for Audit {audit_id} ---")
for r, p, d in recognitions:
    sku = p.sku_code if p else "UNKNOWN"
    print(f"Detection {str(d.id)[:8]} -> SKU: {sku: <8} | Similarity: {r.similarity:.4f} | Margin: {r.margin:.4f}")

