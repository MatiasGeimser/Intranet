from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
import openpyxl
import os
import uuid
import tempfile

router = APIRouter()

# Directorio temporal para los archivos generados
TEMP_DIR = os.path.join(tempfile.gettempdir(), "intranet_excel")
os.makedirs(TEMP_DIR, exist_ok=True)

def remove_temp_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"No se pudo eliminar el archivo temporal {path}: {e}")

@router.post("/process")
async def process_excel(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel (.xlsx)")

    # Leer el archivo original en memoria
    content = await file.read()
    temp_input_path = os.path.join(TEMP_DIR, f"input_{uuid.uuid4().hex}.xlsx")
    with open(temp_input_path, "wb") as f:
        f.write(content)

    try:
        wb = openpyxl.load_workbook(temp_input_path)
        
        seen_phones = set()
        deleted_count = 0
        
        # Iterar sobre las hojas
        for sheet in wb.worksheets:
            if sheet.max_row <= 1:
                continue

            # Revisar la fila 1 (encabezados) para registrar teléfonos sin eliminarla
            for val in next(sheet.iter_rows(min_row=1, max_row=1, values_only=True)):
                if val is not None:
                    val_str = str(val).strip()
                    cleaned_val = ''.join(filter(str.isdigit, val_str))
                    if 7 <= len(cleaned_val) <= 15 and val_str.replace('+','').replace('-','').replace(' ','').isdigit():
                        seen_phones.add(cleaned_val)

            rows_to_keep = []
            
            # Iterar desde la fila 2 en adelante de forma rápida (solo valores)
            for row in sheet.iter_rows(min_row=2, values_only=True):
                row_has_phone = False
                is_duplicate = False
                
                for val in row:
                    if val is not None:
                        val_str = str(val).strip()
                        cleaned_val = ''.join(filter(str.isdigit, val_str))
                        if 7 <= len(cleaned_val) <= 15 and val_str.replace('+','').replace('-','').replace(' ','').isdigit():
                            row_has_phone = True
                            if cleaned_val in seen_phones:
                                is_duplicate = True
                                break
                            else:
                                seen_phones.add(cleaned_val)
                
                if row_has_phone and is_duplicate:
                    deleted_count += 1
                else:
                    rows_to_keep.append(row)
            
            # Borrar todas las filas de datos de una sola vez (muy rápido)
            if sheet.max_row > 1:
                sheet.delete_rows(2, sheet.max_row - 1)
                
            # Reinsertar solo las filas que no son duplicadas
            for row in rows_to_keep:
                sheet.append(row)
        
        # Guardar archivo modificado
        temp_output_path = os.path.join(TEMP_DIR, f"clean_{uuid.uuid4().hex}.xlsx")
        wb.save(temp_output_path)
        
        # Eliminar el archivo de entrada
        remove_temp_file(temp_input_path)
        
        # Generamos un ID de descarga
        download_id = os.path.basename(temp_output_path)
        
        return JSONResponse({
            "message": "Archivo procesado exitosamente.",
            "deleted_count": deleted_count,
            "download_id": download_id
        })
        
    except Exception as e:
        remove_temp_file(temp_input_path)
        print(f"Error procesando el Excel: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {str(e)}")


@router.get("/download/{download_id}")
async def download_excel(
    download_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    # Validar que el archivo exista en nuestro TEMP_DIR para evitar path traversal
    file_path = os.path.join(TEMP_DIR, download_id)
    if not os.path.exists(file_path) or not download_id.startswith("clean_") or ".." in download_id:
        raise HTTPException(status_code=404, detail="Archivo no encontrado o expirado")
        
    background_tasks.add_task(remove_temp_file, file_path)
    
    return FileResponse(
        path=file_path,
        filename="telefonos_limpios.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
