"""Roles con acceso limitado: Practicante tiene los mismos permisos y restricciones que Usuario."""

LIMITED_ROLES = ("Usuario", "Practicante")


def is_limited_role(role_name: str | None) -> bool:
    return (role_name or "Usuario") in LIMITED_ROLES
