from app.core.database import Base
from app.models.role import Role, Permission, role_permissions
from app.models.user import User
from app.models.session import Session
from app.models.credential import Credential
from app.models.event import Event
from app.models.document import Document
from app.models.news import News, Comment
from app.models.audit import AuditLog

# Exponer todo en un solo módulo para facilidad de importación externa
__all__ = [
    "Base",
    "Role",
    "Permission",
    "role_permissions",
    "User",
    "Session",
    "Credential",
    "Event",
    "Document",
    "News",
    "Comment",
    "AuditLog"
]
