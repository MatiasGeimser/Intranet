import os
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentContentUpdate
from app.api.deps import PermissionChecker, get_current_active_user
from app.services.doc_service import doc_service
from app.services.audit_service import audit_service
from app.models.user import User

router = APIRouter()


def user_can_manage_folder(folder: str, current_user: User) -> bool:
    if current_user.role.name == "Administrador":
        return True
    return any(
        permission.folder_name == folder and permission.can_write
        for permission in current_user.folder_permissions
    )


def user_can_access_document(document: Document, current_user: User) -> bool:
    """Comprueba carpeta y visibilidad antes de exponer un documento no administrativo."""
    if current_user.role.name == "Administrador":
        return True

    allowed_folders = {permission.folder_name for permission in current_user.folder_permissions if permission.can_read}
    if document.folder not in allowed_folders:
        return False
    return user_can_manage_folder(document.folder, current_user) or (
        document.is_public
        or document.uploader_id == current_user.id
        or any(user.id == current_user.id for user in document.allowed_users)
    )


@router.get("", response_model=List[DocumentResponse])
def get_documents(
    folder: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("documents:read"))
):
    """Obtiene la lista de documentos, filtrando opcionalmente por carpeta virtual y aplicando controles de acceso."""
    query = db.query(Document)
    if folder:
        query = query.filter(Document.folder == folder)
        
    if current_user.role.name != "Administrador":
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
    current_user: User = Depends(PermissionChecker("documents:read")),
):
    """Entrega las carpetas virtuales permitidas para construir la navegación personal."""
    if current_user.role.name == "Administrador":
        return []
    return [
        {"name": permission.folder_name, "can_write": permission.can_write}
        for permission in current_user.folder_permissions
        if permission.can_read
    ]


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
    if not user_can_manage_folder(folder, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para subir documentos en esta carpeta.")

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
    if current_user.role.name != "Administrador":
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
    if current_user.role.name != "Administrador":
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
    current_user: User = Depends(PermissionChecker("documents:read"))
):
    """Descarga de forma segura un archivo desde el almacenamiento de la Intranet."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    if not user_can_access_document(doc, current_user):
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
    if not user_can_manage_folder(doc.folder, current_user):
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
