import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select

from backend.app.core.database import SessionLocal
from backend.app.models import Role


ROLE_NAMES = ["ADMIN", "MANAGER", "EMPLOYEE"]


def seed_roles():
    db = SessionLocal()

    try:
        for role_name in ROLE_NAMES:
            existing_role = db.scalar(
                select(Role).where(Role.name == role_name)
            )

            if existing_role:
                print(f"ℹ️ Role already exists: {role_name}")
                continue

            db.add(Role(name=role_name))
            print(f"✅ Created role: {role_name}")

        db.commit()
        print("🎉 Role seeding complete.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()