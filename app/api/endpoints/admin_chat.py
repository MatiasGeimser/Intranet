import asyncio
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import bleach
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.models.admin_chat import AdminChatAttachment, AdminChatMessage
from app.models.user import User

router = APIRouter()
CHAT_ROLES = {"Administrador", "Supervisor"}
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


def require_chat_member(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role.name not in CHAT_ROLES:
        raise HTTPException(status_code=403, detail="Este modulo es exclusivo para administradores y supervisores.")
    return current_user


@router.get("/messages")
def list_messages(
    db: Session = Depends(get_db),
    _: User = Depends(require_chat_member),
) -> list[dict[str, Any]]:
    messages = (
        db.query(AdminChatMessage)
        .options(joinedload(AdminChatMessage.sender), joinedload(AdminChatMessage.attachments))
        .order_by(AdminChatMessage.created_at.desc())
        .limit(100)
        .all()
    )
    return [_message_payload(message) for message in reversed(messages)]


@router.get("/participants")
def list_participants(
    db: Session = Depends(get_db),
    _: User = Depends(require_chat_member),
) -> list[dict[str, Any]]:
    users = (
        db.query(User)
        .join(User.role)
        .filter(User.is_active.is_(True), User.role.has(name="Administrador") | User.role.has(name="Supervisor"))
        .order_by(User.full_name.asc())
        .all()
    )
    return [{"id": user.id, "name": user.full_name, "email": user.email, "role": user.role.name} for user in users]


@router.post("/attachments", status_code=201)
async def upload_attachment(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_chat_member),
) -> dict[str, Any]:
    """Sube un adjunto seguro que solo se asociara a un mensaje del emisor."""
    original_name = os.path.basename(file.filename or "archivo")
    extension = Path(original_name).suffix.lower()
    mime_type = (file.content_type or "").lower()
    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS or mime_type not in ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(status_code=415, detail="Tipo de archivo no permitido.")

    content = await file.read(MAX_ATTACHMENT_BYTES + 1)
    if not content or len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="El archivo debe pesar entre 1 byte y 15 MB.")

    CHAT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    file_path = CHAT_UPLOAD_DIR / stored_name
    try:
        file_path.write_bytes(content)
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
    _: User = Depends(require_chat_member),
) -> FileResponse:
    attachment = db.query(AdminChatAttachment).filter(AdminChatAttachment.id == attachment_id).first()
    if not attachment or attachment.message_id is None:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado.")

    file_path = CHAT_UPLOAD_DIR / attachment.stored_name
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="El archivo no esta disponible.")

    safe_name = attachment.original_name.replace('"', "")
    return FileResponse(
        path=file_path,
        media_type=attachment.mime_type,
        headers={"Content-Disposition": f'inline; filename="{safe_name}"'},
    )


class AdminChatManager:
    def __init__(self) -> None:
        self.connections: dict[int, set[WebSocket]] = {}
        self.users: dict[int, dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, user: User, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self.lock:
            self.connections.setdefault(user.id, set()).add(websocket)
            self.users[user.id] = {"id": user.id, "name": user.full_name, "email": user.email}
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
                User.role.has(name="Administrador") | User.role.has(name="Supervisor"),
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
        message = AdminChatMessage(sender_id=user.id, content=content, created_at=datetime.now(timezone.utc))
        for attachment in attachments:
            attachment.message = message
        db.add(message)
        db.commit()
        db.refresh(message)
        await manager.broadcast({"type": "chat_message", "message": _message_payload(message, user)})
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
