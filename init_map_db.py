import asyncio
from app.core.database import SessionLocal, engine, Base
from app.models.workspace import Workspace
from app.models.it_asset import ITAsset
from sqlalchemy import text

def init_db():
    # Creamos las tablas nuevas (si Base.metadata no la ha creado, lo intentamos)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Añadir nuevas columnas a it_assets (sqlite permite ALTER TABLE ADD COLUMN)
        try:
            db.execute(text("ALTER TABLE it_assets ADD COLUMN serial_number VARCHAR(100)"))
            db.execute(text("ALTER TABLE it_assets ADD COLUMN brand VARCHAR(100)"))
            db.execute(text("ALTER TABLE it_assets ADD COLUMN model VARCHAR(100)"))
            db.execute(text("ALTER TABLE it_assets ADD COLUMN last_ping_at DATETIME"))
            db.commit()
        except Exception as e:
            print("Columns might already exist or alter failed:", e)
            db.rollback()

        # Check if workspaces are already created
        existing = db.query(Workspace).count()
        if existing == 0:
            print("Inserting default workspaces P1 to P30")
            # Create P1 to P30 with default pos_x, pos_y based on a grid just for setup
            workspaces = []
            for i in range(1, 31):
                # We'll just distribute them linearly, the user can adjust in the UI later
                # Or set a generic grid
                code = f"P{i}"
                x = (i % 6) * 15.0 + 10.0
                y = (i // 6) * 20.0 + 10.0
                w = Workspace(code=code, pos_x=x, pos_y=y)
                workspaces.append(w)
            
            db.add_all(workspaces)
            db.commit()
            print("Workspaces inserted successfully!")
        else:
            print(f"Workspaces already exist ({existing})")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
