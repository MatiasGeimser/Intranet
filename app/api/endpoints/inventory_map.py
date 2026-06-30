from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.it_asset import ITAsset
from app.models.workspace import Workspace
from app.api.deps import get_current_user
from pydantic import BaseModel
from typing import List, Optional
import json
from sqlalchemy import func
from app.models.pc_login_history import PCLoginHistory

router = APIRouter()

# Schema for the frontend Map
class WorkspaceResponse(BaseModel):
    id: int
    code: str
    pos_x: float
    pos_y: float
    user_id: Optional[int] = None
    asset_id: Optional[int] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    user_area: Optional[str] = None
    asset_hostname: Optional[str] = None
    asset_ip: Optional[str] = None
    asset_status: Optional[str] = None
    asset_serial: Optional[str] = None
    asset_brand: Optional[str] = None
    asset_model: Optional[str] = None

    class Config:
        from_attributes = True

@router.get("/api/inventory-map", response_model=List[WorkspaceResponse])
def get_map_inventory(db: Session = Depends(get_db)):
    workspaces = db.query(Workspace).all()
    response = []
    for w in workspaces:
        res = WorkspaceResponse(
            id=w.id,
            code=w.code,
            pos_x=w.pos_x,
            pos_y=w.pos_y,
            user_id=w.user_id,
            asset_id=w.asset_id,
        )
        if w.user:
            res.user_name = w.user.full_name
            res.user_email = w.user.email
            res.user_role = w.user.role.name if w.user.role else None
            res.user_area = w.user.area.name if w.user.area else None
        if w.asset:
            res.asset_hostname = w.asset.name
            res.asset_ip = w.asset.ip_address
            res.asset_status = w.asset.status
            res.asset_serial = w.asset.serial_number
            res.asset_brand = w.asset.brand
            res.asset_model = w.asset.model
        response.append(res)
    return response

class PositionUpdate(BaseModel):
    id: int
    pos_x: float
    pos_y: float

@router.put("/api/inventory/positions")
def update_positions(updates: List[PositionUpdate], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Simple permissions check could be added here
    for update in updates:
        w = db.query(Workspace).filter(Workspace.id == update.id).first()
        if w:
            w.pos_x = update.pos_x
            w.pos_y = update.pos_y
    db.commit()
    return {"status": "ok"}

class AssignUpdate(BaseModel):
    workspace_id: Optional[int] = None
    code: Optional[str] = None
    user_id: Optional[int] = None
    asset_id: Optional[int] = None

@router.get("/api/inventory-map/options")
def get_assign_options(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.is_active == True).all()
    assets = db.query(ITAsset).filter(ITAsset.status != "Descartado").all()
    return {
        "users": [{"id": u.id, "name": u.full_name, "email": u.email} for u in users],
        "assets": [{"id": a.id, "name": a.name, "ip": a.ip_address} for a in assets]
    }

@router.post("/api/inventory-map/assign")
def assign_workspace(data: AssignUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    w = None
    if data.workspace_id:
        w = db.query(Workspace).filter(Workspace.id == data.workspace_id).first()
        if not w:
            raise HTTPException(status_code=404, detail="Puesto no encontrado")
    elif data.code:
        w = db.query(Workspace).filter(Workspace.code == data.code).first()
        if not w:
            w = Workspace(code=data.code, pos_x=0, pos_y=0)
            db.add(w)
            db.flush()
    else:
        raise HTTPException(status_code=400, detail="Debe proveer workspace_id o code")

    w.user_id = data.user_id
    w.asset_id = data.asset_id
    db.commit()
    return {"status": "ok"}

class LoginReport(BaseModel):
    asset_id: int
    username: str

@router.post("/api/inventory/report-login")
def report_login(data: LoginReport, db: Session = Depends(get_db)):
    """ Endpoint for a PC to report who just logged in. """
    history = PCLoginHistory(asset_id=data.asset_id, username_reported=data.username)
    db.add(history)
    db.commit()
    return {"status": "ok"}

@router.get("/api/inventory-map/recommend-asset/{user_id}")
def recommend_asset(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"asset_id": None}
    
    # 1. Search history for most frequent asset logged into by this user in last 30 days
    # For simplicity, we just count all time
    most_frequent = db.query(
        PCLoginHistory.asset_id, func.count(PCLoginHistory.asset_id).label("cnt")
    ).filter(
        (PCLoginHistory.username_reported == user.full_name) | 
        (PCLoginHistory.username_reported == user.email) |
        (PCLoginHistory.username_reported.ilike(f"%{user.full_name}%"))
    ).group_by(PCLoginHistory.asset_id).order_by(func.count(PCLoginHistory.asset_id).desc()).first()
    
    if most_frequent:
        return {"asset_id": most_frequent.asset_id}
        
    # 2. Fallback: Search ITAsset by assigned_to
    asset = db.query(ITAsset).filter(
        (ITAsset.assigned_to == user.full_name) | 
        (ITAsset.assigned_to == user.email)
    ).first()
    
    if asset:
        return {"asset_id": asset.id}
        
    return {"asset_id": None}

# WebSockets logic
active_connections: List[WebSocket] = []

@router.websocket("/api/inventory/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # No necesitamos procesar mensajes del cliente, solo enviamos estados
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def broadcast_status(message: dict):
    for connection in active_connections:
        try:
            await connection.send_text(json.dumps(message))
        except:
            pass
