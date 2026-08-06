from app.core.database import Base
from app.models.role import Role, Permission, role_permissions
from app.models.user import User
from app.models.session import Session
from app.models.credential import Credential
from app.models.event import Event
from app.models.document import Document
from app.models.news import News, Comment
from app.models.audit import AuditLog
from app.models.phone_number import PhoneNumber
from app.models.task import Task, TaskComment
from app.models.note import Note
from app.models.area import Area
from app.models.collaborator import Collaborator
from app.models.workspace import Workspace
from app.models.folder_access import FolderAccess
from app.models.admin_chat import AdminChatAttachment, AdminChatMessage
from app.models.admin_chat_presence import AdminChatPresence

# Exportar todos los modelos para que Base.metadata.create_all() los encuentre
__all__ = [
    "User", "Role", "Permission", "Session", "Credential", "Event",
    "Document", "News", "Comment", "AuditLog", "ITAsset", "VLAN",
    "NetworkDevice", "PhoneNumber", "Task", "TaskComment", "Note", "Area", "Collaborator",
    "Workspace", "FolderAccess", "AdminChatMessage", "AdminChatAttachment", "AdminChatPresence"
]
