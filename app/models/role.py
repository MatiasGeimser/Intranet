from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

# Tabla intermedia Muchos a Muchos entre Roles y Permisos
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)  # ej. "users:create", "documents:delete"
    description = Column(String(200), nullable=True)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)  # ej. "Administrador", "Supervisor", "Usuario"
    description = Column(String(200), nullable=True)

    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    users = relationship("User", back_populates="role")
