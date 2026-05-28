import os
import re
from sqlalchemy.orm import Session
from typing import Optional, List
from fastapi import UploadFile
from app.models.document import Document
from app.core.config import settings

class DocService:
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitiza el nombre del archivo para evitar inyecciones de ruta o caracteres extraños."""
        # Remover partes de ruta
        filename = os.path.basename(filename)
        # Reemplazar espacios y caracteres inválidos
        filename = re.sub(r"[^\w\.-]", "_", filename)
        return filename

    @staticmethod
    def save_document(
        db: Session,
        upload_file: UploadFile,
        folder: str,
        uploader_id: int
    ) -> Document:
        """Sube y guarda un archivo con versionado automático si ya existe en la misma carpeta."""
        original_name = DocService.sanitize_filename(upload_file.filename)
        base_name, ext = os.path.splitext(original_name)
        
        # Carpeta física en disco
        target_folder_path = os.path.join(settings.UPLOAD_DIR, folder)
        os.makedirs(target_folder_path, exist_ok=True)
        
        # Buscar coincidencias del mismo nombre en la misma carpeta virtual para el versionado
        existing_docs = db.query(Document).filter(
            Document.name == original_name,
            Document.folder == folder
        ).order_by(Document.created_at.desc()).all()
        
        version_num = 1
        if existing_docs:
            # Incrementar la versión
            latest_doc = existing_docs[0]
            try:
                # Extraer número de versión ej: "v2.0" -> 2
                match = re.match(r"v(\d+)\.0", latest_doc.version)
                if match:
                    version_num = int(match.group(1)) + 1
            except Exception:
                version_num = len(existing_docs) + 1
                
        version_str = f"v{version_num}.0"
        
        # Si la versión es > 1, modificamos el nombre del archivo guardado en disco
        saved_filename = original_name if version_num == 1 else f"{base_name}_{version_str}{ext}"
        file_path = os.path.join(target_folder_path, saved_filename)
        
        # Leer y escribir el archivo
        file_content = upload_file.file.read()
        size_bytes = len(file_content)
        
        with open(file_path, "wb") as f:
            f.write(file_content)
            
        # Crear entrada en BD
        # Guardar la ruta relativa para poder servirla por estáticos
        relative_path = os.path.relpath(file_path, start=".")
        
        db_doc = Document(
            name=original_name,
            file_path=relative_path.replace("\\", "/"),
            file_type=ext.lstrip(".").lower(),
            size_bytes=size_bytes,
            folder=folder,
            uploader_id=uploader_id,
            version=version_str
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        
        return db_doc

    @staticmethod
    def get_documents_by_folder(db: Session, folder: str) -> List[Document]:
        """Obtiene la lista de documentos en una carpeta virtual."""
        return db.query(Document).filter(Document.folder == folder).order_by(Document.created_at.desc()).all()

doc_service = DocService()
