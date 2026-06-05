from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.it_asset import ITAsset
from app.schemas.it_asset import ITAssetCreate, ITAssetUpdate, ITAssetResponse
from app.api.deps import get_current_active_user, PermissionChecker
from app.services.audit_service import audit_service
from app.models.user import User
from app.services.excel_import_service import excel_import_service
import os
import tempfile

router = APIRouter()


@router.get("", response_model=List[ITAssetResponse])
def get_assets(
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Obtiene el inventario IT, filtrable por tipo y estado."""
    query = db.query(ITAsset)
    if asset_type:
        query = query.filter(ITAsset.asset_type == asset_type)
    if status:
        query = query.filter(ITAsset.status == status)
    return query.order_by(ITAsset.created_at.desc()).all()


@router.get("/stats")
def get_asset_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Retorna contadores rápidos de activos por tipo y estado."""
    total = db.query(ITAsset).count()
    hardware_active = db.query(ITAsset).filter(
        ITAsset.asset_type == "HARDWARE", ITAsset.status == "Activo"
    ).count()
    software_total = db.query(ITAsset).filter(ITAsset.asset_type == "SOFTWARE").count()
    network_total = db.query(ITAsset).filter(ITAsset.asset_type == "RED").count()
    maintenance = db.query(ITAsset).filter(ITAsset.status == "Mantenimiento").count()
    inactive = db.query(ITAsset).filter(ITAsset.status == "Inactivo").count()

    return {
        "total": total,
        "hardware_active": hardware_active,
        "software_total": software_total,
        "network_total": network_total,
        "maintenance": maintenance,
        "inactive": inactive
    }


@router.post("/import-excel", status_code=status.HTTP_201_CREATED)
async def import_assets_from_excel(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """
    Importa Software y VLANs desde un archivo Excel.
    
    El archivo debe contener dos hojas:
    
    **Hoja 'SOFTWARE':**
    - Columna A: Nombre (obligatorio)
    - Columna B: Variantes
    - Columna C: Versión
    - Columna D: Vendor
    - Columna E: Estado (Activo/Inactivo/Mantenimiento)
    
    **Hoja 'VLAN':**
    - Columna A: ID VLAN (1-4094, obligatorio)
    - Columna B: Nombre (obligatorio)
    - Columna C: Descripción
    - Columna D: Red (ej: 192.168.1.0/24)
    - Columna E: Gateway (ej: 192.168.1.1)
    - Columna F: Estado (Activo/Inactivo)
    
    Retorna un resumen con cantidad de registros importados y errores.
    """
    
    # Validar extensión del archivo
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser Excel (.xlsx o .xls)"
        )
    
    try:
        # Guardar archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            contents = await file.read()
            tmp_file.write(contents)
            tmp_file_path = tmp_file.name
        
        # Procesar el Excel
        import_results = excel_import_service.import_excel(
            file_path=tmp_file_path,
            db=db,
            user_id=current_user.id
        )
        
        # Limpiar archivo temporal
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
        
        # Registrar en auditoría
        audit_service.log_action(
            db=db,
            user_id=current_user.id,
            action="import_assets_excel",
            ip_address=request.client.host if request.client else None,
            details=f"Importó desde Excel: {import_results['software_imported']} software, "
                   f"{import_results['vlan_imported']} VLANs. "
                   f"Errores: {import_results['software_errors']} software, "
                   f"{import_results['vlan_errors']} VLANs."
        )
        
        return {
            "status": "success",
            "summary": {
                "software_imported": import_results["software_imported"],
                "software_errors": import_results["software_errors"],
                "vlan_imported": import_results["vlan_imported"],
                "vlan_errors": import_results["vlan_errors"]
            },
            "messages": import_results["messages"],
            "total_imported": import_results["software_imported"] + import_results["vlan_imported"],
            "total_errors": import_results["software_errors"] + import_results["vlan_errors"]
        }
        
    except Exception as e:
        # Limpiar archivo temporal en caso de error
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
        
        raise HTTPException(
            status_code=400,
            detail=f"Error al procesar Excel: {str(e)}"
        )


@router.post("", response_model=ITAssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    request: Request,
    asset_data: ITAssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Registra un nuevo activo IT en el inventario."""
    db_asset = ITAsset(**asset_data.model_dump(), created_by_id=current_user.id)
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="it_asset_create",
        ip_address=request.client.host if request.client else None,
        details=f"Registró activo IT: {db_asset.name} (Tipo: {db_asset.asset_type})"
    )
    return db_asset


@router.put("/{asset_id}", response_model=ITAssetResponse)
def update_asset(
    asset_id: int,
    request: Request,
    asset_data: ITAssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Actualiza los datos de un activo IT."""
    asset = db.query(ITAsset).filter(ITAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Activo IT no encontrado.")

    for field, value in asset_data.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)

    db.commit()
    db.refresh(asset)

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="it_asset_update",
        ip_address=request.client.host if request.client else None,
        details=f"Actualizó activo IT ID {asset.id} ({asset.name})."
    )
    return asset


@router.delete("/{asset_id}")
def delete_asset(
    asset_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Elimina un activo del inventario IT."""
    asset = db.query(ITAsset).filter(ITAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Activo IT no encontrado.")

    name = asset.name
    db.delete(asset)
    db.commit()

    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="it_asset_delete",
        ip_address=request.client.host if request.client else None,
        details=f"Eliminó activo IT '{name}' del inventario."
    )
    return {"detail": "Activo eliminado exitosamente."}
