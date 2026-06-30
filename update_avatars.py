from app.core.database import SessionLocal
from app.models.user import User
from app.models.it_asset import ITAsset
from app.models.workspace import Workspace
import urllib.parse

def main():
    db = SessionLocal()
    users = db.query(User).all()
    
    updated = 0
    for user in users:
        seed = urllib.parse.quote(user.full_name)
        if user.gender and user.gender.lower() == 'mujer':
            # Female avatar url
            user.avatar_url = f"https://api.dicebear.com/9.x/lorelei/svg?seed={seed}"
        else:
            # Male / default avatar url
            user.avatar_url = f"https://api.dicebear.com/9.x/micah/svg?seed={seed}"
        updated += 1
        
    db.commit()
    print(f"Updated {updated} user avatars.")

if __name__ == "__main__":
    main()
