import os
import csv
import json
import uuid
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add the root directory to sys.path so we can import backend models
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.core.database import SessionLocal
from backend.app.models.product import Product, ProductStatus
from backend.app.models.planogram import Planogram, PlanogramVersion, PlanogramPosition, PlanogramVersionStatus
from backend.app.models.organization import Organization

def seed_data():
    org_id_str = os.environ.get("SEED_ORGANIZATION_ID")
    if not org_id_str:
        print("ERROR: Please export SEED_ORGANIZATION_ID before running this script.")
        print("Example: export SEED_ORGANIZATION_ID='...your-uuid...'")
        sys.exit(1)
        
    try:
        org_id = uuid.UUID(org_id_str)
    except ValueError:
        print("ERROR: SEED_ORGANIZATION_ID must be a valid UUID.")
        sys.exit(1)

    db = SessionLocal()
    
    try:
        # 1. Verify organization exists
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise ValueError(f"Organization with ID {org_id} not found in database.")
            
        print(f"✅ Found Organization: {org.name}")

        base_dir = Path(__file__).parent.parent.parent

        # 2. Seed Products from product_master.csv
        product_csv_path = base_dir / "Dataset" / "product_master.csv"
        if not product_csv_path.exists():
            raise FileNotFoundError(f"{product_csv_path} not found.")
            
        print(f"📦 Seeding Products from {product_csv_path.name}...")
        sku_to_product_id = {}
        
        with open(product_csv_path, mode='r') as f:
            reader = csv.DictReader(f)
            
            # Validate CSV columns
            required_columns = {"sku_id", "product_name", "brand", "category"}
            missing_columns = required_columns - set(reader.fieldnames or [])
            if missing_columns:
                raise ValueError(f"Missing required columns in product_master.csv: {sorted(missing_columns)}")

            for row in reader:
                sku_code = row['sku_id']
                # Upsert logic to avoid constraint violations if run twice
                prod = db.query(Product).filter_by(organization_id=org_id, sku_code=sku_code).first()
                if not prod:
                    prod = Product(
                        organization_id=org_id,
                        sku_code=sku_code,
                        name=row["product_name"],
                        brand=row["brand"],
                        category=row["category"],
                        status=ProductStatus.ACTIVE,
                    )
                    db.add(prod)
                    db.flush() # flush to get the ID immediately
                    
                sku_to_product_id[sku_code] = prod.id

        print("✅ Products prepared.")

        # 3. Seed Planograms from Phase 7 JSONs
        json_dir = base_dir / "Dataset" / "ideal_planograms" / "canonical"
        if not json_dir.exists():
            raise FileNotFoundError(f"{json_dir} not found.")
            
        print("📊 Seeding Planograms and Immutable Versions...")
        for json_file in json_dir.glob("*.json"):
            with open(json_file, 'r') as f:
                data = json.load(f)
                
            plano_code = data["planogram_id"]
            
            plano = db.query(Planogram).filter_by(organization_id=org_id, code=plano_code).first()
            if not plano:
                plano = Planogram(
                    organization_id=org_id,
                    code=plano_code,
                    name=f"Mock Planogram {plano_code}"
                )
                db.add(plano)
                db.flush()
                
            # Create Version 1
            plano_version = db.query(PlanogramVersion).filter_by(planogram_id=plano.id, version_number=1).first()
            if not plano_version:
                plano_version = PlanogramVersion(
                    planogram_id=plano.id,
                    version_number=1,
                    status=PlanogramVersionStatus.PUBLISHED,
                    published_at=datetime.now(timezone.utc)
                )
                db.add(plano_version)
                db.flush()
                
                # Create Positions
                for shelf in data.get("shelves", []):
                    shelf_id = shelf["shelf_id"]
                    for prod_data in shelf.get("products", []):
                        pos = prod_data["position"]
                        sku = prod_data["sku_id"]
                        
                        product_id = sku_to_product_id.get(sku)
                        if not product_id:
                            raise ValueError(
                                f"SKU '{sku}' from planogram '{plano_code}' "
                                f"was not found in product_master.csv."
                            )

                        plano_pos = PlanogramPosition(
                            planogram_version_id=plano_version.id,
                            product_id=product_id,
                            shelf_id=shelf_id,
                            position=pos
                        )
                        db.add(plano_pos)
                            
        db.commit()
        print("✅ Planograms seeded successfully.")
        print("🎉 Phase 7 to Phase 8 transition complete!")

    except Exception as e:
        db.rollback()
        print(f"ERROR: Seed failed: {e}")
        sys.exit(1)
        
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
