import os
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentContentUpdate
from app.api.deps import get_current_active_user
from app.services.doc_service import doc_service
from app.services.audit_service import audit_service
from app.models.user import User
from app.models.folder_access import FolderAccess
from app.services.natura_access import is_natura_manager

router = APIRouter()


class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    parent: str = Field("Natura", min_length=1, max_length=100)


def can_manage_documents(db: Session, current_user: User) -> bool:
    return current_user.role.name == "Administrador" or is_natura_manager(db, current_user)


def require_document_reader(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> User:
    if can_manage_documents(db, current_user) or "documents:read" in {permission.code for permission in current_user.role.permissions}:
        return current_user
    raise HTTPException(status_code=403, detail="No tienes acceso al gestor documental.")


def user_can_manage_folder(folder: str, current_user: User, db: Session) -> bool:
    if can_manage_documents(db, current_user):
        return True
    if folder == "Natura" or folder.startswith("Natura / "):
        return False
    return any(
        permission.folder_name == folder and permission.can_write
        for permission in current_user.folder_permissions
    )


def user_can_access_document(document: Document, current_user: User, db: Session) -> bool:
    """Comprueba carpeta y visibilidad antes de exponer un documento no administrativo."""
    if can_manage_documents(db, current_user):
        return True

    allowed_folders = {permission.folder_name for permission in current_user.folder_permissions if permission.can_read}
    if document.folder not in allowed_folders:
        return False
    return user_can_manage_folder(document.folder, current_user, db) or (
        document.is_public
        or document.uploader_id == current_user.id
        or any(user.id == current_user.id for user in document.allowed_users)
    )


def get_natura_personal_owner(db: Session, folder: str) -> User | None:
    parts = [part.strip() for part in folder.split(" / ")]
    if len(parts) < 3 or parts[0] != "Natura" or parts[1] != "CBE":
        return None
    return db.query(User).filter(func.lower(User.full_name) == parts[2].lower()).first()


@router.get("", response_model=List[DocumentResponse])
def get_documents(
    folder: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_document_reader)
):
    """Obtiene la lista de documentos, filtrando opcionalmente por carpeta virtual y aplicando controles de acceso."""
    query = db.query(Document)
    if folder:
        query = query.filter(Document.folder == folder)
        
    if not can_manage_documents(db, current_user):
        allowed_folders = [f.folder_name for f in current_user.folder_permissions if f.can_read]
        query = query.filter(Document.folder.in_(allowed_folders))
        
        # Usuarios regulares / Supervisores solo ven documentos públicos, los subidos por ellos mismos o los que les han compartido explícitamente.
        managed_folders = [f.folder_name for f in current_user.folder_permissions if f.can_write]
        visibility_filter = (
            (Document.is_public == True)
            | (Document.uploader_id == current_user.id)
            | (Document.allowed_users.any(User.id == current_user.id))
        )
        query = query.filter(or_(Document.folder.in_(managed_folders), visibility_filter))
        
    return query.order_by(Document.created_at.desc()).all()


@router.get("/folders")
def get_accessible_folders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_document_reader),
):
    """Entrega las carpetas virtuales permitidas para construir la navegación personal."""
    if can_manage_documents(db, current_user):
        names = {name for (name,) in db.query(FolderAccess.folder_name).distinct().all()}
        names.update(name for (name,) in db.query(Document.folder).distinct().all())
        return [{"name": name, "can_write": True} for name in sorted(names)]
    return [
        {"name": permission.folder_name, "can_write": permission.can_write}
        for permission in current_user.folder_permissions
        if permission.can_read
    ]


@router.post("/folders", status_code=status.HTTP_201_CREATED)
def create_folder(
    payload: FolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Crea una carpeta virtual dentro del gestor documental."""
    if not can_manage_documents(db, current_user):
        raise HTTPException(status_code=403, detail="Solo un administrador documental puede crear carpetas.")
    name = " ".join(payload.name.strip().split())
    parent = " / ".join(part.strip() for part in payload.parent.split(" / ") if part.strip())
    if not name or "/" in name or parent != "Natura" and not parent.startswith("Natura / "):
        raise HTTPException(status_code=400, detail="La carpeta debe pertenecer a Natura y tener un nombre válido.")
    folder_name = f"{parent} / {name}"
    if len(folder_name) > 100:
        raise HTTPException(status_code=400, detail="La ruta de la carpeta es demasiado larga.")
    if db.query(FolderAccess).filter(FolderAccess.folder_name == folder_name).first():
        raise HTTPException(status_code=409, detail="La carpeta ya existe.")
    db.add(FolderAccess(user_id=current_user.id, folder_name=folder_name, can_read=True, can_write=True))
    db.commit()
    return {"name": folder_name, "can_write": True}


@router.delete("/folders")
def delete_folder(
    folder: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Elimina una carpeta virtual vacía y sus permisos asociados."""
    if not can_manage_documents(db, current_user):
        raise HTTPException(status_code=403, detail="Solo un administrador documental puede eliminar carpetas.")
    if folder == "Natura" or not folder.startswith("Natura / "):
        raise HTTPException(status_code=400, detail="No se puede eliminar la raíz Natura.")
    prefix = f"{folder} / "
    if db.query(Document).filter(or_(Document.folder == folder, Document.folder.like(f"{prefix}%"))).first():
        raise HTTPException(status_code=409, detail="La carpeta no está vacía.")
    db.query(FolderAccess).filter(or_(FolderAccess.folder_name == folder, FolderAccess.folder_name.like(f"{prefix}%"))).delete(synchronize_session=False)
    db.commit()
    return {"detail": "Carpeta eliminada.", "folder": folder}


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    request: Request,
    folder: str = Form("General"),
    file: UploadFile = File(...),
    is_public: bool = Form(True),
    allowed_users: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Sube un archivo a una carpeta virtual específica de la intranet."""
    # Verificar permisos de escritura en la carpeta
    if not user_can_manage_folder(folder, current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para subir documentos en esta carpeta.")

    personal_owner = None
    if can_manage_documents(db, current_user):
        personal_owner = get_natura_personal_owner(db, folder)
        if folder.startswith("Natura / CBE /") and not personal_owner:
            raise HTTPException(status_code=400, detail="No se pudo identificar al usuario dueño de esta carpeta Natura.")
        if personal_owner:
            is_public = False
            allowed_users = str(personal_owner.id)

    allowed_users_ids = []
    if not is_public and allowed_users:
        try:
            allowed_users_ids = [int(u_id.strip()) for u_id in allowed_users.split(",") if u_id.strip()]
        except ValueError:
            pass

    # Guardar documento usando el servicio que maneja versionamiento automático
    db_doc = doc_service.save_document(
        db=db,
        upload_file=file,
        folder=folder,
        uploader_id=current_user.id,
        is_public=is_public,
        allowed_users_ids=allowed_users_ids
    )

    # Registrar en auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="document_upload",
        ip_address=request.client.host if request.client else None,
        details=f"Subió el archivo '{db_doc.name}' (versión {db_doc.version}, {db_doc.size_bytes} bytes) en la carpeta '{db_doc.folder}'"
    )

    return db_doc


@router.get("/{doc_id}/preview")
def preview_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Permite ver y editar contenidos simples directamente desde la Intranet (solo Administradores)."""
    if not can_manage_documents(db, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso restringido a administradores.")

    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    try:
        preview = doc_service.read_document_preview(doc)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "document": {
            "id": doc.id,
            "name": doc.name,
            "file_type": doc.file_type,
            "version": doc.version,
            "folder": doc.folder,
            "size_bytes": doc.size_bytes,
            "created_at": doc.created_at
        },
        "preview": preview
    }


@router.put("/{doc_id}/content")
def update_document_content(
    doc_id: int,
    update_data: DocumentContentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Guarda cambios en el documento desde la vista de edición (solo Administradores)."""
    if not can_manage_documents(db, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso restringido a administradores.")

    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    try:
        updated_doc = doc_service.save_document_content(
            db=db,
            doc=doc,
            content=update_data.content,
            rows=update_data.rows,
            sheet_name=update_data.sheet_name
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="document_edit",
        ip_address=request.client.host if request.client else None,
        details=f"Editó el archivo '{updated_doc.name}' (ID {updated_doc.id}) en la carpeta '{updated_doc.folder}'"
    )

    return {"detail": "Documento guardado correctamente.", "document": {
        "id": updated_doc.id,
        "size_bytes": updated_doc.size_bytes,
        "version": updated_doc.version
    }}


@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_document_reader)
):
    """Descarga de forma segura un archivo desde el almacenamiento de la Intranet."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    if not user_can_access_document(doc, current_user, db):
        raise HTTPException(status_code=403, detail="No tienes acceso a este documento.")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="El archivo físico no existe en el servidor.")

    # Registrar en auditoría la descarga de información confidencial
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="document_download",
        ip_address=request.client.host if request.client else None,
        details=f"Descargó el archivo '{doc.name}' (ID {doc.id}, versión {doc.version})"
    )

    # Retornar el archivo directamente
    return FileResponse(
        path=doc.file_path,
        filename=doc.name,
        media_type="application/octet-stream"
    )


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Elimina permanentemente un documento de la base de datos y del disco."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    if not user_can_manage_folder(doc.folder, current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para eliminar documentos en esta carpeta.")

    # Eliminar físicamente del disco si existe
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            # Continuamos aunque falle el borrado físico para evitar cuelgues, pero lo registramos en logs
            pass

    name = doc.name
    folder = doc.folder
    db.delete(doc)
    db.commit()

    # Auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="document_delete",
        ip_address=request.client.host if request.client else None,
        details=f"Eliminó el archivo '{name}' de la carpeta '{folder}'"
    )

    return {"detail": f"Archivo '{name}' eliminado de forma definitiva."}
