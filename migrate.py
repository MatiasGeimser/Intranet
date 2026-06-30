import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine, Base
from app.models.it_asset import ITAsset
from app.models.user import User
from app.models.pc_login_history import PCLoginHistory
from app.models.pc_login_history import PCLoginHistory

print("Creating PCLoginHistory table...")
Base.metadata.create_all(bind=engine)
print("Done!")
