from sqlalchemy.orm import Session

from app.models.folder_access import FolderAccess
from app.models.user import User


def get_natura_folder_names(db: Session) -> set[str]:
    """Returns the complete Natura folder catalog used to identify managers."""
    return {
        name
        for (name,) in db.query(FolderAccess.folder_name)
        .filter(FolderAccess.folder_name.like("Natura / %"))
        .distinct()
        .all()
    }


def is_natura_manager(db: Session, user: User) -> bool:
    """A Natura manager must have read/write access to every Natura folder."""
    natura_folders = get_natura_folder_names(db)
    if not natura_folders:
        return False
    assigned = {
        permission.folder_name
        for permission in user.folder_permissions
        if permission.can_read and permission.can_write
    }
    return natura_folders.issubset(assigned)
