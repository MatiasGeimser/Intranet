from app.core.database import engine, Base
from app.models.document import Document
import sqlalchemy

Base.metadata.create_all(bind=engine)
with engine.connect() as conn:
    try:
        conn.execute(sqlalchemy.text('ALTER TABLE documents ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT true'))
        conn.commit()
        print('Database schema updated')
    except Exception as e:
        print('Error:', e)
