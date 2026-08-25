import asyncio
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import bleach
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from pydantic import BaseModel, Field

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.models.admin_chat import AdminChatAttachment, AdminChatMessage
from app.models.admin_chat_presence import AdminChatPresence
from app.models.role import Role
from app.models.user import User
from app.services.supabase_storage import SupabaseStorageError, supabase_storage

router = APIRouter()
# Vercel solo permite escritura en UPLOAD_DIR (/tmp en producción).
CHAT_UPLOAD_DIR = Path(settings.UPLOAD_DIR) / "chat"
MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024
ALLOWED_ATTACHMENT_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
}
ALLOWED_ATTACHMENT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".docx", ".xlsx", ".pptx", ".txt"}


class ChatMessageCreate(BaseModel):
    recipient_id: int
    content: str = ""
    attachment_ids: list[int] = Field(default_factory=list)


def require_chat_member(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role.name == "Usuario":
        raise HTTPException(status_code=403, detail="Este módulo no está disponible para usuarios estándar.")
    return current_user


@router.get("/messages")
def list_messages(
    after_id: int = 0,
    contact_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_member),
) -> list[dict[str, Any]]:
    query = (
        db.query(AdminChatMessage)
        .options(joinedload(AdminChatMessage.sender), joinedload(AdminChatMessage.attachments))
    )
    if contact_id is None:
        # El antiguo canal institucional queda fuera de circulación: solo conversaciones directas.
        return []
    if contact_id == current_user.id:
        return []
    contact = (
            db.query(User)
            .join(User.role)
            .filter(
                User.id == contact_id,
                User.is_active.is_(True),
                Role.name != "Usuario",
            )
            .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado.")
    query = query.filter(
        or_(
            and_(AdminChatMessage.sender_id == current_user.id, AdminChatMessage.recipient_id == contact_id),
            and_(AdminChatMessage.sender_id == contact_id, AdminChatMessage.recipient_id == current_user.id),
        )
    )
    if after_id > 0:
        query = query.filter(AdminChatMessage.id > after_id)
    messages = query.order_by(AdminChatMessage.created_at.desc()).limit(100).all()
    return [_message_payload(message) for message in reversed(messages)]


@router.get("/incoming")
def list_incoming_messages(
    after_id: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_member),
) -> list[dict[str, Any]]:
    """Devuelve los mensajes entrantes dirigidos al usuario actual para disparar notificaciones en tiempo real."""
    query = (
        db.query(AdminChatMessage)
        .options(joinedload(AdminChatMessage.sender), joinedload(AdminChatMessage.attachments))
        .filter(AdminChatMessage.recipient_id == current_user.id)
    )
    if after_id > 0:
        query = query.filter(AdminChatMessage.id > after_id)
    messages = query.order_by(AdminChatMessage.created_at.desc()).limit(50).all()
    return [_message_payload(message) for message in reversed(messages)]


@router.post("/messages", status_code=201)
async def send_chat_message(
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_member),
) -> dict[str, Any]:
    content = bleach.clean(payload.content or "", tags=[], attributes={}, strip=True).strip()
    attachment_ids = payload.attachment_ids or []
    if len(attachment_ids) > 5 or (not content and not attachment_ids) or len(content) > 2000:
        raise HTTPException(status_code=400, detail="Mensaje no válido o excede el límite permitido.")

    attachments = []
    if attachment_ids:
        attachments = (
            db.query(AdminChatAttachment)
            .filter(
                AdminChatAttachment.id.in_(attachment_ids),
                AdminChatAttachment.uploader_id == current_user.id,
                AdminChatAttachment.message_id.is_(None),
            )
            .all()
        )
        if len(attachments) != len(attachment_ids):
            raise HTTPException(status_code=400, detail="Uno o más adjuntos no son válidos.")

    recipient = (
        db.query(User)
        .join(User.role)
        .filter(
            User.id == payload.recipient_id,
            User.is_active.is_(True),
            Role.name != "Usuario",
        )
        .first()
    )
    if not recipient:
        raise HTTPException(status_code=404, detail="Destinatario no encontrado o no autorizado.")

    message = AdminChatMessage(
        sender_id=current_user.id,
        recipient_id=recipient.id,
        content=content,
        created_at=datetime.now(timezone.utc),
    )
    for attachment in attachments:
        attachment.message = message
    db.add(message)
    db.commit()
    db.refresh(message)
    _record_presence(current_user.id)

    response_payload = _message_payload(message, current_user)
    event = {"type": "chat_message", "message": response_payload}
    await manager.send_to(current_user.id, event)
    await manager.send_to(recipient.id, event)

    return response_payload


@router.get("/participants")
def list_participants(
    db: Session = Depends(get_db),
    _: User = Depends(require_chat_member),
) -> list[dict[str, Any]]:
    users = (
        db.query(User)
        .join(User.role)
        .filter(User.is_active.is_(True), Role.name != "Usuario")
        .order_by(User.full_name.asc())
        .all()
    )
    return [{"id": user.id, "name": user.full_name, "email": user.email, "role": user.role.name} for user in users]


@router.get("/presence")
def list_presence(
    db: Session = Depends(get_db),
    _: User = Depends(require_chat_member),
) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
    from datetime import timedelta
    cutoff -= timedelta(seconds=30)
    rows = (
        db.query(AdminChatPresence, User)
        .join(User, User.id == AdminChatPresence.user_id)
        .join(User.role)
        .filter(
            User.is_active.is_(True),
            Role.name != "Usuario",
            AdminChatPresence.last_seen >= cutoff,
        )
        .all()
    )
    return [
        {"id": user.id, "name": user.full_name, "email": user.email, "role": user.role.name}
        for _, user in rows
    ]


@router.post("/presence/heartbeat")
def heartbeat_presence(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_member),
) -> dict[str, bool]:
    presence = db.query(AdminChatPresence).filter(AdminChatPresence.user_id == current_user.id).first()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if presence:
        presence.last_seen = now
    else:
        db.add(AdminChatPresence(user_id=current_user.id, last_seen=now))
    db.commit()
    return {"ok": True}


@router.post("/attachments", status_code=201)
async def upload_attachment(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_member),
) -> dict[str, Any]:
    """Sube un adjunto seguro que se almacena en Supabase Storage para persistencia multi-dispositivo."""
    original_name = os.path.basename(file.filename or "archivo")
    extension = Path(original_name).suffix.lower()
    mime_type = (file.content_type or "").lower()
    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS or mime_type not in ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(status_code=415, detail="Tipo de archivo no permitido.")

    content = await file.read(MAX_ATTACHMENT_BYTES + 1)
    if not content or len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="El archivo debe pesar entre 1 byte y 15 MB.")

    stored_name = f"{uuid4().hex}{extension}"
    object_path = f"chat/{stored_name}"

    if supabase_storage.enabled:
        try:
            supabase_storage.upload_bytes(object_path, content, mime_type)
        except Exception as exc:
            # No registrar un adjunto que no podrán abrir los dos participantes.
            raise HTTPException(
                status_code=503,
                detail="No fue posible guardar el archivo de forma segura. Intenta nuevamente.",
            ) from exc
    elif os.getenv("VERCEL"):
        # El disco de una función serverless es temporal y no sirve para conversaciones compartidas.
        raise HTTPException(
            status_code=503,
            detail="El almacenamiento seguro del chat no está disponible. Intenta nuevamente más tarde.",
        )

    # Guardar también copia local en UPLOAD_DIR (/tmp)
    CHAT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = CHAT_UPLOAD_DIR / stored_name
    try:
        file_path.write_bytes(content)
    except Exception:
        pass

    try:
        attachment = AdminChatAttachment(
            uploader_id=current_user.id,
            original_name=original_name[:255],
            stored_name=stored_name,
            mime_type=mime_type,
            size_bytes=len(content),
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
    except Exception:
        if file_path.exists():
            file_path.unlink()
        db.rollback()
        raise

    return _attachment_payload(attachment)


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_member),
) -> Response:
    attachment = db.query(AdminChatAttachment).filter(AdminChatAttachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado.")

    if attachment.message_id is not None:
        message = db.query(AdminChatMessage).filter(AdminChatMessage.id == attachment.message_id).first()
        if not message or current_user.id not in {message.sender_id, message.recipient_id}:
            raise HTTPException(status_code=403, detail="No tienes acceso a este adjunto.")
    elif attachment.uploader_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este adjunto.")

    safe_name = attachment.original_name.replace('"', "")

    # 1. Intentar desde Supabase Storage (persistente en Serverless)
    if supabase_storage.enabled:
        try:
            object_path = attachment.stored_name if attachment.stored_name.startswith("chat/") else f"chat/{attachment.stored_name}"
            data = supabase_storage.download_bytes(object_path)
            return Response(
                content=data,
                media_type=attachment.mime_type,
                headers={
                    "Content-Disposition": f'inline; filename="{safe_name}"',
                    "Cache-Control": "private, max-age=300",
                },
            )
        except Exception:
            pass

    # 2. Fallback a almacenamiento local
    local_name = attachment.stored_name.split("/")[-1]
    file_path = CHAT_UPLOAD_DIR / local_name
    if file_path.is_file():
        return FileResponse(
            path=file_path,
            media_type=attachment.mime_type,
            headers={
                "Content-Disposition": f'inline; filename="{safe_name}"',
                "Cache-Control": "private, max-age=300",
            },
        )

    raise HTTPException(status_code=404, detail="El archivo no está disponible.")


def _record_presence(user_id: int) -> None:
    db = SessionLocal()
    try:
        presence = db.query(AdminChatPresence).filter(AdminChatPresence.user_id == user_id).first()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if presence:
            presence.last_seen = now
        else:
            db.add(AdminChatPresence(user_id=user_id, last_seen=now))
        db.commit()
    finally:
        db.close()


class AdminChatManager:
    def __init__(self) -> None:
        self.connections: dict[int, set[WebSocket]] = {}
        self.users: dict[int, dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, user: User, websocket: WebSocket) -> None:
        await websocket.accept()
        role_name = user.role.name if user.role else "Supervisor"
        async with self.lock:
            self.connections.setdefault(user.id, set()).add(websocket)
            self.users[user.id] = {"id": user.id, "name": user.full_name, "email": user.email, "role": role_name}
        _record_presence(user.id)
        await self.broadcast({"type": "presence", "users": list(self.users.values())})

    async def disconnect(self, user_id: int, websocket: WebSocket | None = None) -> None:
        async with self.lock:
            if websocket:
                connections = self.connections.get(user_id, set())
                connections.discard(websocket)
                if not connections:
                    self.connections.pop(user_id, None)
                    self.users.pop(user_id, None)
            else:
                self.connections.pop(user_id, None)
                self.users.pop(user_id, None)
        await self.broadcast({"type": "presence", "users": list(self.users.values())})

    async def send_to(self, user_id: int, payload: dict[str, Any]) -> None:
        for websocket in list(self.connections.get(user_id, set())):
            try:
                await websocket.send_json(payload)
            except Exception:
                await self.disconnect(user_id, websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        for user_id in list(self.connections):
            await self.send_to(user_id, payload)


manager = AdminChatManager()


@router.websocket("/ws")
async def admin_chat_websocket(websocket: WebSocket) -> None:
    user = _websocket_admin(websocket)
    if not user:
        await websocket.close(code=1008)
        return

    await manager.connect(user, websocket)
    try:
        while True:
            raw_payload = await websocket.receive_text()
            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                continue

            message_type = payload.get("type")
            if message_type == "chat":
                await _handle_chat_message(user, payload)
            elif message_type == "signal":
                await _handle_signal(user, payload)
    except WebSocketDisconnect:
        await manager.disconnect(user.id, websocket)
    except Exception:
        await manager.disconnect(user.id, websocket)


def _websocket_admin(websocket: WebSocket) -> User | None:
    token = websocket.cookies.get("access_token")
    if not token:
        authorization = websocket.headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
        if payload.get("type") != "access":
            return None
    except (JWTError, TypeError, ValueError):
        return None

    db = SessionLocal()
    try:
        return (
            db.query(User)
            .join(User.role)
            .filter(
                User.id == user_id,
                User.is_active.is_(True),
                Role.name != "Usuario",
            )
            .first()
        )
    finally:
        db.close()


async def _handle_chat_message(user: User, payload: dict[str, Any]) -> None:
    content = bleach.clean(str(payload.get("content", "")), tags=[], attributes={}, strip=True).strip()
    attachment_ids = payload.get("attachment_ids", [])
    if not isinstance(attachment_ids, list) or len(attachment_ids) > 5:
        return
    try:
        attachment_ids = [int(attachment_id) for attachment_id in attachment_ids]
    except (TypeError, ValueError):
        return
    if len(set(attachment_ids)) != len(attachment_ids) or (not content and not attachment_ids) or len(content) > 2000:
        return

    db = SessionLocal()
    try:
        attachments = []
        if attachment_ids:
            attachments = (
                db.query(AdminChatAttachment)
                .filter(
                    AdminChatAttachment.id.in_(attachment_ids),
                    AdminChatAttachment.uploader_id == user.id,
                    AdminChatAttachment.message_id.is_(None),
                )
                .all()
            )
            if len(attachments) != len(attachment_ids):
                return
        recipient_id = payload.get("recipient_id")
        recipient = None
        if recipient_id is None:
            return
        try:
            recipient_id = int(recipient_id)
        except (TypeError, ValueError):
            return
        if recipient_id == user.id:
            return
        recipient = (
            db.query(User)
            .join(User.role)
            .filter(
                User.id == recipient_id,
                User.is_active.is_(True),
                Role.name != "Usuario",
            )
            .first()
        )
        if not recipient:
            return
        message = AdminChatMessage(
            sender_id=user.id,
            recipient_id=recipient_id,
            content=content,
            created_at=datetime.now(timezone.utc),
        )
        for attachment in attachments:
            attachment.message = message
        db.add(message)
        db.commit()
        db.refresh(message)
        event = {"type": "chat_message", "message": _message_payload(message, user)}
        await manager.send_to(user.id, event)
        await manager.send_to(recipient.id, event)
    finally:
        db.close()


async def _handle_signal(user: User, payload: dict[str, Any]) -> None:
    target_id = payload.get("target_id")
    signal = payload.get("signal")
    if not isinstance(target_id, int) or not isinstance(signal, dict):
        return

    kind = signal.get("kind")
    if kind not in {"offer", "answer", "ice", "reject", "end"}:
        return
    await manager.send_to(target_id, {"type": "signal", "from": user.id, "signal": signal})


def _message_payload(message: AdminChatMessage, sender: User | None = None) -> dict[str, Any]:
    author = sender or message.sender
    return {
        "id": message.id,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "recipient_id": message.recipient_id,
        "sender": {"id": author.id, "name": author.full_name, "email": author.email},
        "attachments": [_attachment_payload(attachment) for attachment in message.attachments],
    }


def _attachment_payload(attachment: AdminChatAttachment) -> dict[str, Any]:
    return {
        "id": attachment.id,
        "name": attachment.original_name,
        "mime_type": attachment.mime_type,
        "size_bytes": attachment.size_bytes,
        "url": f"/api/admin-chat/attachments/{attachment.id}/download",
    }
