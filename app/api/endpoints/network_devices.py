from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.network_devices import SwitchDevice, SwitchInterface
from app.models.workspace import Workspace
from app.schemas.network_devices import (
    SwitchDeviceResponse, 
    SwitchDeviceDetailResponse,
    SwitchInterfaceResponse,
    SwitchInterfaceUpdate
)
from app.api.deps import PermissionChecker
from app.services.audit_service import audit_service
from app.services.network_device_import_service import network_device_import_service
from app.models.user import User
import os
import tempfile

router = APIRouter()


def ensure_interface_management_columns(db: Session) -> None:
    """Añade campos de gestión a instalaciones existentes sin requerir una migración manual."""
    columns = {column["name"] for column in inspect(db.bind).get_columns("switch_interfaces")}
    statements = []
    if "is_enabled" not in columns:
        statements.append("ALTER TABLE switch_interfaces ADD COLUMN is_enabled BOOLEAN NOT NULL DEFAULT TRUE")
    if "workspace_id" not in columns:
        statements.append("ALTER TABLE switch_interfaces ADD COLUMN workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL")

    if not statements:
        return

    try:
        for statement in statements:
            db.execute(text(statement))
        db.commit()
    except Exception:
        db.rollback()
        raise


@router.get("/workspaces")
def get_workspace_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Puestos disponibles para asociar físicamente un puerto del switch."""
    ensure_interface_management_columns(db)
    return [{"id": workspace.id, "code": workspace.code} for workspace in db.query(Workspace).order_by(Workspace.code).all()]


@router.get("", response_model=List[SwitchDeviceResponse])
def get_switches(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Obtiene lista de Switches configurados"""
    ensure_interface_management_columns(db)
    query = db.query(SwitchDevice)
    if status:
        query = query.filter(SwitchDevice.status == status)
    return query.order_by(SwitchDevice.hostname).all()


@router.get("/{switch_id}", response_model=SwitchDeviceDetailResponse)
def get_switch_details(
    switch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Obtiene detalles completos de un Switch con todas sus interfaces"""
    ensure_interface_management_columns(db)
    switch = db.query(SwitchDevice).filter(SwitchDevice.id == switch_id).first()
    if not switch:
        raise HTTPException(status_code=404, detail="Switch no encontrado.")
    return switch


@router.get("/{switch_id}/interfaces", response_model=List[SwitchInterfaceResponse])
def get_switch_interfaces(
    switch_id: int,
    connected_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Obtiene interfaces de un Switch"""
    ensure_interface_management_columns(db)
    query = db.query(SwitchInterface).filter(SwitchInterface.switch_id == switch_id)
    
    if connected_only:
        query = query.filter(SwitchInterface.description.contains("ENDPOINT"))
    
    return query.order_by(SwitchInterface.interface_name).all()


@router.get("/{switch_id}/stats")
def get_switch_stats(
    switch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Obtiene estadísticas de uso de puertos de un Switch"""
    ensure_interface_management_columns(db)
    interfaces = db.query(SwitchInterface).filter(
        SwitchInterface.switch_id == switch_id
    ).all()
    
    total = len(interfaces)
    connected = sum(1 for i in interfaces if i.is_enabled and "CONECTADO" in (i.description or "").upper())
    free = sum(1 for i in interfaces if i.is_enabled and "LIBRE" in (i.description or "").upper())
    uplinks = sum(1 for i in interfaces if i.is_uplink)
    trunks = sum(1 for i in interfaces if i.is_trunk)
    
    return {
        "total_ports": total,
        "connected_devices": connected,
        "free_ports": free,
        "uplink_ports": uplinks,
        "trunk_ports": trunks,
        "utilization_percent": round((connected / total * 100) if total > 0 else 0, 2)
    }


@router.post("/import-cisco-config", status_code=status.HTTP_201_CREATED)
async def import_cisco_switch_config(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """
    Importa configuración completa de un Switch Cisco desde Excel.
    
    El archivo debe tener la estructura:
    - Fila 1: Encabezados (HOSTNAME, IP)
    - Fila 2: Datos del switch
    - Fila 4: Encabezados de datos
    - Fila 5+: VLANs (izquierda) e Interfaces (derecha)
    """
    
    # Validar extensión
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser Excel (.xlsx o .xls)"
        )
    
    tmp_file_path = None
    
    try:
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            contents = await file.read()
            tmp_file.write(contents)
            tmp_file_path = tmp_file.name
        
        # Procesar configuración
        import_results = network_device_import_service.import_switch_config(
            file_path=tmp_file_path,
            db=db,
            user_id=current_user.id
        )
        
        # Auditoría
        audit_service.log_action(
            db=db,
            user_id=current_user.id,
            action="import_switch_config",
            ip_address=request.client.host if request.client else None,
            details=f"Importó switch: {import_results['vlans_imported']} VLANs, "
                   f"{import_results['interfaces_imported']} interfaces"
        )
        
        return {
            "status": "success",
            "switch_id": import_results["switch_id"],
            "switch_created": import_results["switch_created"],
            "summary": {
                "vlans_imported": import_results["vlans_imported"],
                "vlans_errors": import_results["vlans_errors"],
                "interfaces_imported": import_results["interfaces_imported"],
                "interfaces_errors": import_results["interfaces_errors"]
            },
            "messages": import_results["messages"],
            "total_imported": (import_results["vlans_imported"] + 
                             import_results["interfaces_imported"]),
            "total_errors": (import_results["vlans_errors"] + 
                           import_results["interfaces_errors"])
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error al procesar: {str(e)}"
        )
    
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


@router.put("/interfaces/{interface_id}", response_model=SwitchInterfaceResponse)
def update_switch_interface(
    interface_id: int,
    request: Request,
    iface_data: SwitchInterfaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("it:manage"))
):
    """Actualiza selectivamente la VLAN, descripción y tipo de dispositivo de una interfaz."""
    ensure_interface_management_columns(db)
    iface = db.query(SwitchInterface).filter(SwitchInterface.id == interface_id).first()
    if not iface:
        raise HTTPException(status_code=404, detail="Interfaz no encontrada.")

    # Guardamos los valores anteriores para la auditoría
    old_vlan = iface.vlan_name
    old_desc = iface.description
    old_type = iface.connected_device_type
    old_workspace_id = iface.workspace_id
    old_enabled = iface.is_enabled

    # Modificar SOLO los campos indicados por el usuario
    if iface_data.vlan_name is not None:
        iface.vlan_name = iface_data.vlan_name
    if iface_data.description is not None:
        iface.description = iface_data.description
    if iface_data.connected_device_type is not None:
        iface.connected_device_type = iface_data.connected_device_type
    if iface_data.is_enabled is not None:
        iface.is_enabled = iface_data.is_enabled
    if iface_data.workspace_id is not None:
        workspace = db.query(Workspace).filter(Workspace.id == iface_data.workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Puesto de trabajo no encontrado.")
        iface.workspace_id = workspace.id
    elif "workspace_id" in iface_data.model_fields_set:
        iface.workspace_id = None

    db.commit()
    db.refresh(iface)

    # Log de auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="update_switch_interface",
        ip_address=request.client.host if request.client else None,
        details=f"Modificó interfaz {iface.interface_name} de {iface.switch.hostname}. "
                f"VLAN: '{old_vlan}' -> '{iface.vlan_name}', "
                f"Desc: '{old_desc}' -> '{iface.description}', "
                f"Tipo: '{old_type}' -> '{iface.connected_device_type}', "
                f"Puesto: '{old_workspace_id}' -> '{iface.workspace_id}', "
                f"Habilitada: '{old_enabled}' -> '{iface.is_enabled}'"
    )

    return iface

