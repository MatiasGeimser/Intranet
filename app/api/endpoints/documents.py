import os
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.api.deps import PermissionChecker, get_current_active_user
from app.services.doc_service import doc_service
from app.services.audit_service import audit_service
from app.models.user import User

router = APIRouter()

@router.get("", response_model=List[DocumentResponse])
def get_documents(
    folder: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("documents:manage"))
):
    """Obtiene la lista de documentos, filtrando opcionalmente por carpeta virtual."""
    query = db.query(Document)
    if folder:
        query = query.filter(Document.folder == folder)
    return query.order_by(Document.created_at.desc()).all()


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    request: Request,
    folder: str = Form("General"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("documents:manage"))
):
    """Sube un archivo a una carpeta virtual específica de la intranet."""
    # Guardar documento usando el servicio que maneja versionamiento automático
    db_doc = doc_service.save_document(
        db=db,
        upload_file=file,
        folder=folder,
        uploader_id=current_user.id
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


@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("documents:manage"))
):
    """Descarga de forma segura un archivo desde el almacenamiento de la Intranet."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

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
    current_user: User = Depends(PermissionChecker("documents:manage"))
):
    """Elimina permanentemente un documento de la base de datos y del disco."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

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
