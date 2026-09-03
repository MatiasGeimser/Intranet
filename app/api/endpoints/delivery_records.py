import hashlib
import json
import secrets
import base64
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.delivery_record import DeliveryRecord
from app.models.user import User
from app.schemas.delivery_record import (
    DeliveryRecordCreate,
    DeliveryRecordDetail,
    DeliveryRecordSummary,
    PublicSignatureCreate,
    ReturnedEquipment,
)
from app.services.audit_service import audit_service
from app.services.email_service import EmailService
from app.services.delivery_record_pdf import build_delivery_record_pdf

router = APIRouter()
SIGNATURE_LINK_VALIDITY_DAYS = 7


def can_manage_delivery_records(user: User) -> bool:
    return user.role and user.role.name == "Administrador"


def require_delivery_record_manager(user: User = Depends(get_current_active_user)) -> User:
    if not can_manage_delivery_records(user):
        raise HTTPException(status_code=403, detail="No tienes permiso para gestionar actas de entrega.")
    return user


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_signature_token() -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=SIGNATURE_LINK_VALIDITY_DAYS)
    return token, _hash_token(token), expires_at


def _signature_url(token: str) -> str:
    return f"{settings.APP_BASE_URL.rstrip('/')}/actas/firma/{token}"


def _loads(value: str, fallback):
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback


def _document_payload(record: DeliveryRecord) -> dict:
    """Campos que forman el contenido inalterable del acta, sin secretos."""
    return {
        "reference": record.reference,
        "delivery_date": record.delivery_date.isoformat(),
        "site": record.site,
        "recipient_name": record.recipient_name,
        "recipient_email": record.recipient_email,
        "recipient_run": record.recipient_run,
        "recipient_role": record.recipient_role,
        "recipient_unit": record.recipient_unit,
        "employment_type": record.employment_type,
        "equipment_type": record.equipment_type,
        "equipment_brand_model": record.equipment_brand_model,
        "equipment_hostname": record.equipment_hostname,
        "equipment_serial": record.equipment_serial,
        "mac_address": record.mac_address,
        "monitor_serial": record.monitor_serial,
        "dock_serial": record.dock_serial,
        "accessories": _loads(record.accessories_json, []),
        "delivery_condition": record.delivery_condition,
        "label_number": record.label_number,
        "migration": _loads(record.migration_json, []),
        "returned_equipment": _loads(record.returned_equipment_json, {}),
        "observations": record.observations,
    }


def _document_hash(record: DeliveryRecord) -> str:
    serialized = json.dumps(_document_payload(record), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _serialize(record: DeliveryRecord, signature_token: str | None = None) -> dict:
    return {
        "id": record.id,
        "reference": record.reference,
        "recipient_name": record.recipient_name,
        "recipient_email": record.recipient_email,
        "recipient_run": record.recipient_run,
        "recipient_role": record.recipient_role,
        "recipient_unit": record.recipient_unit,
        "employment_type": record.employment_type,
        "delivery_date": record.delivery_date,
        "site": record.site,
        "equipment_type": record.equipment_type,
        "equipment_brand_model": record.equipment_brand_model,
        "equipment_hostname": record.equipment_hostname,
        "equipment_serial": record.equipment_serial,
        "mac_address": record.mac_address,
        "monitor_serial": record.monitor_serial,
        "dock_serial": record.dock_serial,
        "accessories": _loads(record.accessories_json, []),
        "delivery_condition": record.delivery_condition,
        "label_number": record.label_number,
        "migration": _loads(record.migration_json, []),
        "returned_equipment": _loads(record.returned_equipment_json, {}),
        "observations": record.observations,
        "status": record.status,
        "created_at": record.created_at,
        "signature_expires_at": record.signature_expires_at,
        "recipient_signed_at": record.recipient_signed_at,
        "recipient_signature_data": record.recipient_signature_data,
        "recipient_signer_name": record.recipient_signer_name,
        "content_hash": record.content_hash,
        "signed_document_hash": record.signed_document_hash,
        "created_by_name": record.created_by.full_name if record.created_by else "",
        "signature_url": _signature_url(signature_token) if signature_token else None,
    }


def _get_record_or_404(db: Session, record_id: int) -> DeliveryRecord:
    record = db.query(DeliveryRecord).filter(DeliveryRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Acta no encontrada.")
    return record


@router.get("", response_model=List[DeliveryRecordSummary])
def list_delivery_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_record_manager),
):
    return db.query(DeliveryRecord).order_by(DeliveryRecord.created_at.desc()).all()


@router.get("/recipients")
def list_recipients(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_record_manager),
):
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()
    return [{
        "id": user.id,
        "name": user.full_name,
        "email": user.email,
        "role": user.role.name if user.role else "",
        "area": user.area.name if user.area else "",
    } for user in users]


@router.post("", response_model=DeliveryRecordDetail, status_code=status.HTTP_201_CREATED)
def create_delivery_record(
    payload: DeliveryRecordCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_record_manager),
):
    recipient = db.query(User).filter(User.id == payload.recipient_id, User.is_active.is_(True)).first() if payload.recipient_id else None
    token, token_hash, expires_at = _new_signature_token()
    reference = f"ACTA-{datetime.now(timezone.utc):%Y}-{secrets.randbelow(900000) + 100000}"
    while db.query(DeliveryRecord.id).filter(DeliveryRecord.reference == reference).first():
        reference = f"ACTA-{datetime.now(timezone.utc):%Y}-{secrets.randbelow(900000) + 100000}"

    record = DeliveryRecord(
        reference=reference,
        created_by_id=current_user.id,
        recipient_id=recipient.id if recipient else None,
        signature_token_hash=token_hash,
        signature_expires_at=expires_at,
        **payload.model_dump(exclude={"accessories", "migration", "returned_equipment"}),
        accessories_json=json.dumps(payload.accessories),
        migration_json=json.dumps(payload.migration),
        returned_equipment_json=payload.returned_equipment.model_dump_json(),
    )
    if recipient:
        record.recipient_name = recipient.full_name
        record.recipient_email = recipient.email
        record.recipient_role = recipient.role.name if recipient.role else record.recipient_role
        record.recipient_unit = recipient.area.name if recipient.area else record.recipient_unit
    record.content_hash = _document_hash(record)
    db.add(record)
    db.commit()
    db.refresh(record)
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="delivery_record_created",
        ip_address=request.client.host if request.client else None,
        details=f"Creó acta de entrega {record.reference} para {record.recipient_name}.",
    )
    return _serialize(record, token)


@router.get("/{record_id}", response_model=DeliveryRecordDetail)
def get_delivery_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_record_manager),
):
    return _serialize(_get_record_or_404(db, record_id))


@router.post("/{record_id}/renew-signature-link", response_model=DeliveryRecordDetail)
def renew_signature_link(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_record_manager),
):
    record = _get_record_or_404(db, record_id)
    if record.status == "signed":
        raise HTTPException(status_code=400, detail="El acta ya está firmada y no puede recibir otro enlace.")
    token, record.signature_token_hash, record.signature_expires_at = _new_signature_token()
    db.commit()
    audit_service.log_action(
        db=db, user_id=current_user.id, action="delivery_record_link_renewed",
        ip_address=request.client.host if request.client else None,
        details=f"Renovó enlace de firma para {record.reference}.",
    )
    return _serialize(record, token)


@router.post("/{record_id}/send-signature-link")
def send_signature_link(
    record_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_record_manager),
):
    record = _get_record_or_404(db, record_id)
    if record.status == "signed":
        raise HTTPException(status_code=400, detail="El acta ya fue firmada.")
    if not record.recipient_email:
        raise HTTPException(status_code=400, detail="Esta acta no tiene correo del receptor.")
    token, record.signature_token_hash, record.signature_expires_at = _new_signature_token()
    db.commit()
    background_tasks.add_task(
        EmailService.send_delivery_signature_email,
        record.recipient_email,
        record.recipient_name,
        record.reference,
        _signature_url(token),
        record.signature_expires_at,
    )
    audit_service.log_action(
        db=db, user_id=current_user.id, action="delivery_record_signature_sent",
        ip_address=request.client.host if request.client else None,
        details=f"Envió enlace de firma para {record.reference}.",
    )
    return {
        "detail": "Enlace de firma enviado al correo del receptor.",
        "signature_url": _signature_url(token),
    }


@router.get("/{record_id}/integrity")
def validate_integrity(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_record_manager),
):
    record = _get_record_or_404(db, record_id)
    current_hash = _document_hash(record)
    return {
        "valid": current_hash == record.content_hash,
        "content_hash": record.content_hash,
        "signed_document_hash": record.signed_document_hash,
        "status": record.status,
    }


@router.get("/{record_id}/pdf")
def download_delivery_record_pdf(
    record_id: int,
    inline: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_delivery_record_manager),
):
    record = _get_record_or_404(db, record_id)
    if record.status != "signed" or not record.signed_document_hash:
        raise HTTPException(status_code=400, detail="El PDF oficial estará disponible cuando el receptor firme el acta.")
    if _document_hash(record) != record.content_hash:
        raise HTTPException(status_code=409, detail="La validación de integridad falló; no se puede emitir este documento.")
    pdf = build_delivery_record_pdf(record, record.signed_document_hash)
    filename = f"{record.reference}.pdf"
    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{"inline" if inline else "attachment"}; filename="{filename}"'},
    )


@router.post("/sign/{token}")
def sign_delivery_record(
    token: str,
    payload: PublicSignatureCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    record = db.query(DeliveryRecord).filter(DeliveryRecord.signature_token_hash == _hash_token(token)).first()
    now = datetime.now(timezone.utc)
    if not record or record.status == "signed" or record.signature_expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=404, detail="El enlace de firma no es válido o ya expiró.")
    if not payload.signature_data.startswith("data:image/png;base64,"):
        raise HTTPException(status_code=400, detail="La firma debe ser una imagen PNG válida.")
    try:
        base64.b64decode(payload.signature_data.split(",", 1)[1], validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="La imagen de firma no es válida.") from exc

    record.recipient_signature_data = payload.signature_data
    record.recipient_signer_name = payload.signer_name.strip()
    record.recipient_signed_at = now
    record.recipient_signature_ip = request.client.host if request.client else None
    record.status = "signed"
    signed_payload = "|".join([
        record.content_hash,
        record.recipient_signature_data,
        record.recipient_signer_name,
        record.recipient_signed_at.isoformat(),
    ])
    record.signed_document_hash = hashlib.sha256(signed_payload.encode("utf-8")).hexdigest()
    db.commit()
    audit_service.log_action(
        db=db, user_id=record.created_by_id, action="delivery_record_signed",
        ip_address=record.recipient_signature_ip,
        details=f"El receptor firmó digitalmente el acta {record.reference}.",
    )
    return {"detail": "Firma registrada correctamente."}
