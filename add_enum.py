from backend.app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text("ALTER TYPE auditstatus ADD VALUE 'NEEDS_RETAKE'"))
    conn.commit()
print("Done")
