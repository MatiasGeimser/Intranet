import os
from app.core.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE credentials ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;"))
            conn.commit()
            print("Migration success")
        except Exception as e:
            print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
