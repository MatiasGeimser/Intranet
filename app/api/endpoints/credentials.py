from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.credential import Credential
from app.schemas.credential import CredentialResponse, CredentialCreate, CredentialUpdate
from app.api.deps import get_current_active_user, PermissionChecker
from app.services.crypto_service import crypto_service
from app.services.audit_service import audit_service
from app.models.user import User

router = APIRouter()

@router.get("", response_model=List[CredentialResponse])
def get_credentials(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("credentials:manage"))
):
    """Obtiene la bóveda de contraseñas filtradas por categoría (si se especifica)."""
    query = db.query(Credential)
    
    # Si no es Administrador, solo puede ver sus propias credenciales
    if current_user.role.name != "Administrador":
        query = query.filter(Credential.owner_id == current_user.id)
        
    if category:
        query = query.filter(Credential.category == category)
        
    return query.order_by(Credential.created_at.desc()).all()


@router.post("", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
def create_credential(
    request: Request,
    cred_data: CredentialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("credentials:manage"))
):
    """Crea y guarda una credencial encriptando la contraseña con AES-256-GCM."""
    encrypted_pw = crypto_service.encrypt_password(cred_data.password)
    
    db_cred = Credential(
        title=cred_data.title,
        url=cred_data.url,
        username=cred_data.username,
        encrypted_password=encrypted_pw,
        category=cred_data.category,
        owner_id=current_user.id
    )
    db.add(db_cred)
    db.commit()
    db.refresh(db_cred)

    # Auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="credential_create",
        ip_address=request.client.host if request.client else None,
        details=f"Creó una nueva credencial en la bóveda: {db_cred.title} (Categoría: {db_cred.category})"
    )

    return db_cred


@router.get("/{cred_id}/decrypt")
def decrypt_credential_password(
    cred_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("credentials:manage"))
):
    """Desencripta de forma segura una credencial y registra obligatoriamente la auditoría de acceso."""
    cred = db.query(Credential).filter(Credential.id == cred_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credencial no encontrada.")
        
    # Verificar propiedad (solo administradores pueden saltarse esto)
    if current_user.role.name != "Administrador" and cred.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para acceder a esta credencial de seguridad."
        )

    # Desencriptar e inyectar auditoría
    decrypted_pw = crypto_service.decrypt_password(
        encrypted_password=cred.encrypted_password,
        db=db,
        user_id=current_user.id,
        credential_id=cred.id,
        ip_address=request.client.host if request.client else None
    )

    return {"password": decrypted_pw}


@router.put("/{cred_id}", response_model=CredentialResponse)
def update_credential(
    cred_id: int,
    request: Request,
    cred_data: CredentialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("credentials:manage"))
):
    """Actualiza los datos de una credencial en la bóveda."""
    cred = db.query(Credential).filter(Credential.id == cred_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credencial no encontrada.")
        
    if current_user.role.name != "Administrador" and cred.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")

    if cred_data.title:
        cred.title = cred_data.title
    if cred_data.url is not None:
        cred.url = cred_data.url
    if cred_data.username:
        cred.username = cred_data.username
    if cred_data.category:
        cred.category = cred_data.category
    if cred_data.password:
        cred.encrypted_password = crypto_service.encrypt_password(cred_data.password)

    db.commit()
    db.refresh(cred)

    # Auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="credential_update",
        ip_address=request.client.host if request.client else None,
        details=f"Modificó la credencial ID {cred.id} ({cred.title})."
    )

    return cred


@router.delete("/{cred_id}")
def delete_credential(
    cred_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("credentials:manage"))
):
    """Elimina una credencial de la bóveda."""
    cred = db.query(Credential).filter(Credential.id == cred_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credencial no encontrada.")
        
    if current_user.role.name != "Administrador" and cred.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")

    title = cred.title
    db.delete(cred)
    db.commit()

    # Auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="credential_delete",
        ip_address=request.client.host if request.client else None,
        details=f"Eliminó permanentemente la credencial '{title}' de la bóveda."
    )

    return {"detail": "Credencial eliminada exitosamente."}
