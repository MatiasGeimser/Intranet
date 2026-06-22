from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.credential import Credential

db_url = 'postgresql://postgres.ondyyjkceprlfkorlvnp:xsgnAjSyekoUiA5v@aws-1-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require'
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Get all credentials ordered by ID descending (newest first)
all_creds = db.query(Credential).order_by(Credential.id.desc()).all()

seen = set()
deleted_count = 0

for c in all_creds:
    # Only process executive credentials (the ones with ' - ' in title)
    dash_idx = c.title.find(' - ')
    if dash_idx != -1:
        sys_label = c.title[:dash_idx].strip()
        person_name = c.title[dash_idx + 3:].strip()
        
        # We use (owner_id, sys_label, person_name) as the unique key
        key = (c.owner_id, sys_label, person_name)
        
        if key in seen:
            print(f"Deleting duplicate: {c.id} {c.title}")
            db.delete(c)
            deleted_count += 1
        else:
            seen.add(key)

db.commit()
print(f"Deleted {deleted_count} duplicates.")
