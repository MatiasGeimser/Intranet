"""Puente privado para el asistente ITSM; no usa cookies del navegador."""

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.api.endpoints import admin_chat
from app.core.config import settings
from app.core.database import get_db
from app.models.role import Role
from app.models.user import User

router = APIRouter()
MAX_ASSERTION_LIFETIME_SECONDS = 120


def _decode_assertion(authorization: str | None) -> dict[str, Any]:
    secret = (settings.ASSISTANT_BRIDGE_SECRET or "").strip()
    if len(secret) < 32:
        raise HTTPException(status_code=503, detail="La integración del asistente no está configurada.")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Credencial de integración requerida.")

    try:
        encoded, signature = authorization.removeprefix("Bearer ").split(".", 1)
        expected = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("firma")
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding))
        now = int(time.time())
        if (
            payload.get("v") != 1
            or payload.get("aud") != "intranet-chat"
            or not isinstance(payload.get("email"), str)
            or payload.get("iat", 0) > now + 30
            or payload.get("exp", 0) <= now - 30
            or payload["exp"] - payload["iat"] > MAX_ASSERTION_LIFETIME_SECONDS
        ):
            raise ValueError("payload")
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Credencial de integración inválida.")


def assistant_chat_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    payload = _decode_assertion(authorization)
    user = (
        db.query(User)
        .join(User.role)
        .filter(User.email.ilike(payload["email"].strip()), User.is_active.is_(True), Role.name != "Usuario")
        .first()
    )
    if not user:
        raise HTTPException(status_code=403, detail="Tu cuenta no tiene acceso al chat institucional.")
    return user


@router.get("/chat/participants")
def participants(db: Session = Depends(get_db), user: User = Depends(assistant_chat_user)):
    return [participant for participant in admin_chat.list_participants(db=db, _=user) if participant["id"] != user.id]


@router.get("/chat/messages")
def messages(contact_id: int, after_id: int = 0, db: Session = Depends(get_db), user: User = Depends(assistant_chat_user)):
    return admin_chat.list_messages(contact_id=contact_id, after_id=after_id, db=db, current_user=user)


@router.get("/chat/incoming")
def incoming(after_id: int = 0, db: Session = Depends(get_db), user: User = Depends(assistant_chat_user)):
    return admin_chat.list_incoming_messages(after_id=after_id, db=db, current_user=user)


@router.post("/chat/messages", status_code=201)
async def send_message(
    payload: admin_chat.ChatMessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(assistant_chat_user),
):
    return await admin_chat.send_chat_message(payload=payload, db=db, current_user=user)
