from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.models.user import User
from app.models.collaborator import Collaborator
from app.models.credential import Credential
from app.models.it_asset import ITAsset
from app.api.deps import get_current_active_user

router = APIRouter()

@router.get("")
def global_search(q: str = "", db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    Realiza una búsqueda global (Omnibar).
    """
    results = {
        "collaborators": [],
        "credentials": [],
        "assets": []
    }
    
    if not q or len(q) < 2:
        return results

    search_term = f"%{q}%"

    # 1. Buscar Colaboradores
    collabs = db.query(Collaborator).filter(
        or_(
            Collaborator.full_name.ilike(search_term),
            Collaborator.email.ilike(search_term),
            Collaborator.position.ilike(search_term)
        )
    ).limit(5).all()
    
    for c in collabs:
        results["collaborators"].append({
            "id": c.id,
            "name": c.full_name,
            "subtitle": c.position or "Colaborador",
            "avatar": c.avatar_url,
            "link": "/directory"
        })

    # 2. Buscar Contraseñas (dependiendo del rol)
    if current_user.role.name == "Administrador":
        creds = db.query(Credential).filter(
            Credential.title.ilike(search_term)
        ).limit(5).all()
    elif current_user.role.name == "Supervisor":
        creds = db.query(Credential).filter(
            Credential.title.ilike(search_term),
            Credential.is_active == True
        ).limit(5).all()
    else:
        # Standard user
        creds = db.query(Credential).filter(
            Credential.title.ilike(search_term),
            Credential.is_active == True,
            or_(
                Credential.owner_id == current_user.id,
                Credential.title.ilike(f"%{current_user.full_name}%")
            )
        ).limit(3).all()
        
    for c in creds:
        results["credentials"].append({
            "id": c.id,
            "name": c.title,
            "subtitle": c.category,
            "link": "/passwords"
        })

    # 3. Buscar Inventario IT (Solo Admins)
    if current_user.role.name == "Administrador":
        assets = db.query(ITAsset).filter(
            or_(
                ITAsset.name.ilike(search_term),
                ITAsset.ip_address.ilike(search_term)
            )
        ).limit(3).all()
        
        for a in assets:
            results["assets"].append({
                "id": a.id,
                "name": a.name,
                "subtitle": a.ip_address or "Sin IP",
                "link": "/it-assets"
            })

    return results
