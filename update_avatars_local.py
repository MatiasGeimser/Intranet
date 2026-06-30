from app.core.database import SessionLocal
from app.models.user import User
from app.models.workspace import Workspace
from app.models.it_asset import ITAsset
from app.models.event import Event
from app.models.task import Task
from app.models.document import Document
from app.models.credential import Credential

def main():
    db = SessionLocal()
    users = db.query(User).all()
    
    updated = 0
    for user in users:
        if user.gender and user.gender.lower() == 'mujer':
            user.avatar_url = "/static/uploads/avatars/woman.png"
        else:
            user.avatar_url = "/static/uploads/avatars/man.png"
        updated += 1
        
    db.commit()
    print(f"Updated {updated} user avatars to the correct existing PNG files.")

if __name__ == "__main__":
    main()
