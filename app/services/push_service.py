"""Envío de notificaciones Web Push (VAPID) a los dispositivos suscritos de un usuario."""
import json
import logging
from typing import Optional

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)


def push_enabled() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def send_push_to_user(
    user_id: int,
    title: str,
    body: str,
    url: str = "/admin-chat",
    tag: Optional[str] = None,
) -> int:
    """Envía la notificación a todos los dispositivos del usuario. Devuelve cuántos la recibieron.

    Abre su propia sesión de base de datos para poder ejecutarse en segundo plano
    después de responder la petición. Las suscripciones vencidas se eliminan.
    """
    if not push_enabled():
        return 0
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:  # pragma: no cover - dependencia opcional en desarrollo
        logger.warning("pywebpush no está instalado; se omiten notificaciones push.")
        return 0

    payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag})
    delivered = 0
    db = SessionLocal()
    try:
        subscriptions = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()
        for subscription in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                    },
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": settings.VAPID_SUBJECT},
                    ttl=60 * 60 * 24,
                    headers={"Urgency": "high"},
                    timeout=10,
                )
                delivered += 1
            except WebPushException as exc:
                status_code = getattr(exc.response, "status_code", None)
                if status_code in (404, 410):
                    # El navegador anuló la suscripción (app desinstalada, permisos revocados...).
                    db.delete(subscription)
                else:
                    logger.warning("Fallo push para usuario %s: %s", user_id, exc)
            except Exception as exc:  # red, timeouts, etc.
                logger.warning("Error inesperado enviando push a usuario %s: %s", user_id, exc)
        db.commit()
    finally:
        db.close()
    return delivered


def notify_chat_message(recipient_id: int, sender_id: int, sender_name: str, content: str, has_attachments: bool) -> None:
    """Notificación estilo WhatsApp: agrupada por conversación con el remitente."""
    text = (content or "").strip()
    if not text and has_attachments:
        text = "📎 Te envió un archivo adjunto"
    if len(text) > 140:
        text = text[:137] + "..."
    send_push_to_user(
        recipient_id,
        title=sender_name,
        body=text or "Nuevo mensaje",
        url=f"/admin-chat?contact={sender_id}",
        tag=f"chat-{sender_id}",
    )
