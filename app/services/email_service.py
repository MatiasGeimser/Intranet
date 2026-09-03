import logging
import smtplib
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_delivery_signature_email(
        recipient_email: str,
        recipient_name: str,
        record_reference: str,
        signature_url: str,
        expires_at,
    ) -> bool:
        """Envía el enlace seguro para firmar un acta desde cualquier teléfono."""
        expiration = expires_at.strftime("%d-%m-%Y %H:%M")
        subject = f"Firma requerida: acta de entrega {record_reference}"
        html_content = f"""
        <!DOCTYPE html>
        <html><head><meta charset="utf-8"></head>
        <body style="margin:0;padding:24px;background:#F4F6F8;font-family:Segoe UI,Arial,sans-serif;color:#262523;">
            <div style="max-width:600px;margin:auto;background:#FFFFFF;border:1px solid #E5E7EB;border-radius:16px;overflow:hidden;">
                <div style="padding:24px 28px;background:#049DD9;color:#FFFFFF;">
                    <h1 style="margin:0;font-size:20px;">Acta de entrega pendiente de firma</h1>
                </div>
                <div style="padding:28px;line-height:1.55;">
                    <p>Hola, {escape(recipient_name)}:</p>
                    <p>Tienes una acta de entrega y recepción de equipamiento pendiente de confirmación.</p>
                    <p style="padding:14px 16px;background:#F4F6F8;border-radius:8px;"><strong>Referencia:</strong> {escape(record_reference)}</p>
                    <p>Abre el siguiente enlace desde tu celular o computador, revisa la información y firma directamente en la pantalla.</p>
                    <p style="text-align:center;margin:28px 0;">
                        <a href="{escape(signature_url, quote=True)}" style="display:inline-block;padding:13px 22px;background:#049DD9;color:#FFFFFF;text-decoration:none;border-radius:8px;font-weight:700;">Revisar y firmar acta</a>
                    </p>
                    <p style="font-size:12px;color:#6B7280;">El enlace vence el {expiration}. No lo reenvíes a otras personas.</p>
                </div>
                <div style="padding:16px 28px;background:#F8F9FA;border-top:1px solid #E5E7EB;color:#8C8C8C;font-size:11px;">Correo automático de GEIMSER. No responder.</div>
            </div>
        </body></html>
        """
        return EmailService._send_html_email(recipient_email, subject, html_content)

    @staticmethod
    def send_task_assigned_email(
        recipient_email: str,
        recipient_name: str,
        task_title: str,
        assigner_name: str,
        note_title: str
    ) -> bool:
        """Envía una notificación institucional al asignar una tarea."""
        subject = f"Nueva tarea asignada: {task_title}"
        
        # Plantilla HTML con diseño corporativo premium
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
                    background-color: #F8F9FA;
                    color: #333333;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 40px auto;
                    background-color: #FFFFFF;
                    border-radius: 24px;
                    overflow: hidden;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
                    border: 1px solid rgba(140, 140, 140, 0.15);
                }}
                .header {{
                    background: linear-gradient(135deg, #049DD9 0%, #0385B8 100%);
                    padding: 40px 30px;
                    text-align: center;
                    color: #FFFFFF;
                }}
                .header h1 {{
                    font-size: 22px;
                    margin: 0;
                    font-weight: 700;
                    letter-spacing: -0.5px;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .greeting {{
                    font-size: 16px;
                    font-weight: 600;
                    margin-bottom: 20px;
                    color: #1A1A1A;
                }}
                .info-box {{
                    background-color: #F4F6F8;
                    border-radius: 16px;
                    padding: 20px;
                    margin: 24px 0;
                    border-left: 4px solid #049DD9;
                }}
                .info-row {{
                    display: flex;
                    margin-bottom: 12px;
                    font-size: 14px;
                }}
                .info-row:last-child {{
                    margin-bottom: 0;
                }}
                .info-label {{
                    font-weight: 700;
                    color: #8C8C8C;
                    width: 120px;
                    flex-shrink: 0;
                }}
                .info-value {{
                    color: #1A1A1A;
                    font-weight: 500;
                }}
                .btn-container {{
                    text-align: center;
                    margin-top: 30px;
                }}
                .btn {{
                    background-color: #049DD9;
                    color: #FFFFFF;
                    padding: 12px 30px;
                    text-decoration: none;
                    font-size: 14px;
                    font-weight: 700;
                    border-radius: 14px;
                    display: inline-block;
                    box-shadow: 0 4px 12px rgba(4, 157, 217, 0.25);
                }}
                .footer {{
                    background-color: #F8F9FA;
                    padding: 20px 30px;
                    text-align: center;
                    font-size: 11px;
                    color: #8C8C8C;
                    border-top: 1px solid rgba(140, 140, 140, 0.1);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Notificación de Tarea Asignada</h1>
                </div>
                <div class="content">
                    <p class="greeting">Hola, {recipient_name}:</p>
                    <p style="font-size: 14px; line-height: 1.6; color: #4A4A4A;">
                        Se te ha asignado una nueva tarea en la plataforma corporativa. A continuación, encontrarás los detalles:
                    </p>
                    
                    <div class="info-box">
                        <div class="info-row">
                            <span class="info-label">Tarea:</span>
                            <span class="info-value">{task_title}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Proyecto / Nota:</span>
                            <span class="info-value">{note_title}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Asignado por:</span>
                            <span class="info-value">{assigner_name}</span>
                        </div>
                    </div>
                    
                    <div class="btn-container">
                        <a href="{settings.APP_BASE_URL.rstrip('/')}/dashboard" class="btn" style="color: #FFFFFF;">Ver en Intranet</a>
                    </div>
                </div>
                <div class="footer">
                    <p>Este es un correo automático enviado por {settings.PROJECT_NAME}. Por favor no respondas a este mensaje.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return EmailService._send_html_email(recipient_email, subject, html_content)

    @staticmethod
    def send_task_status_changed_email(
        recipient_email: str,
        recipient_name: str,
        task_title: str,
        previous_status: str,
        current_status: str,
        updated_by_name: str,
        note_title: str,
    ) -> bool:
        """Avisa al creador cuando el encargado mueve una tarea en el tablero."""
        status_labels = {
            "pending": "Por hacer", "todo": "Por hacer", "inprogress": "En curso",
            "inreview": "En revisión", "completed": "Finalizada", "done": "Finalizada",
        }
        previous_label = status_labels.get(previous_status, previous_status)
        current_label = status_labels.get(current_status, current_status)
        subject = f"Actualización de tarea: {task_title}"
        html_content = f"""
        <!DOCTYPE html>
        <html><head><meta charset="utf-8"></head>
        <body style="margin:0;padding:24px;background:#F8F9FA;font-family:Segoe UI,Arial,sans-serif;color:#1A1A1A;">
            <div style="max-width:600px;margin:auto;background:#FFFFFF;border:1px solid #E5E7EB;border-radius:16px;overflow:hidden;">
                <div style="padding:24px 28px;background:#049DD9;color:#FFFFFF;">
                    <h1 style="margin:0;font-size:20px;">Actualización de tarea</h1>
                </div>
                <div style="padding:28px;">
                    <p style="margin-top:0;">Hola, {escape(recipient_name)}:</p>
                    <p>La tarea que asignaste cambió de estado en el tablero.</p>
                    <div style="margin:20px 0;padding:18px;background:#F4F6F8;border-left:4px solid #049DD9;border-radius:8px;">
                        <p style="margin:0 0 10px;"><strong>Tarea:</strong> {escape(task_title)}</p>
                        <p style="margin:0 0 10px;"><strong>Proyecto:</strong> {escape(note_title)}</p>
                        <p style="margin:0 0 10px;"><strong>Movimiento:</strong> {escape(previous_label)} → {escape(current_label)}</p>
                        <p style="margin:0;"><strong>Actualizada por:</strong> {escape(updated_by_name)}</p>
                    </div>
                    <a href="{settings.APP_BASE_URL.rstrip('/')}/dashboard" style="display:inline-block;padding:12px 20px;background:#049DD9;color:#FFFFFF;text-decoration:none;border-radius:8px;font-weight:700;">Ver tarea en Intranet</a>
                </div>
            </div>
        </body></html>
        """
        return EmailService._send_html_email(recipient_email, subject, html_content)

    @staticmethod
    def send_task_comment_email(
        recipient_email: str,
        recipient_name: str,
        task_title: str,
        comment_content: str,
        author_name: str,
        note_title: str,
    ) -> bool:
        """Avisa a la otra parte cuando se registra un avance en una tarea."""
        subject = f"Nuevo avance en tarea: {task_title}"
        html_content = f"""
        <!DOCTYPE html>
        <html><head><meta charset="utf-8"></head>
        <body style="margin:0;padding:24px;background:#F8F9FA;font-family:Segoe UI,Arial,sans-serif;color:#1A1A1A;">
            <div style="max-width:600px;margin:auto;background:#FFFFFF;border:1px solid #E5E7EB;border-radius:16px;overflow:hidden;">
                <div style="padding:24px 28px;background:#049DD9;color:#FFFFFF;">
                    <h1 style="margin:0;font-size:20px;">Nuevo avance de tarea</h1>
                </div>
                <div style="padding:28px;">
                    <p style="margin-top:0;">Hola, {escape(recipient_name)}:</p>
                    <p>{escape(author_name)} registró un avance en una tarea compartida contigo.</p>
                    <div style="margin:20px 0;padding:18px;background:#F4F6F8;border-left:4px solid #049DD9;border-radius:8px;">
                        <p style="margin:0 0 10px;"><strong>Tarea:</strong> {escape(task_title)}</p>
                        <p style="margin:0 0 10px;"><strong>Proyecto:</strong> {escape(note_title)}</p>
                        <p style="margin:0;"><strong>Avance:</strong><br>{escape(comment_content).replace(chr(10), '<br>')}</p>
                    </div>
                    <a href="{settings.APP_BASE_URL.rstrip('/')}/dashboard" style="display:inline-block;padding:12px 20px;background:#049DD9;color:#FFFFFF;text-decoration:none;border-radius:8px;font-weight:700;">Ver tarea en Intranet</a>
                </div>
            </div>
        </body></html>
        """
        return EmailService._send_html_email(recipient_email, subject, html_content)

    @staticmethod
    def _send_html_email(recipient_email: str, subject: str, html_content: str) -> bool:
        smtp_user = settings.SMTP_USER
        smtp_password = settings.SMTP_PASSWORD
        smtp_host = settings.SMTP_HOST
        smtp_port = settings.SMTP_PORT
        smtp_use_ssl = settings.SMTP_USE_SSL
        smtp_sender = settings.SMTP_SENDER

        logger.info("Enviando notificación de tarea a %s.", recipient_email)
        if not smtp_user or not smtp_password:
            logger.error("SMTP no configurado: no se pudo enviar la notificación a %s.", recipient_email)
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{smtp_sender}>"
            msg["To"] = recipient_email
            msg.attach(MIMEText(html_content, "html"))

            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) if smtp_use_ssl else smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.ehlo()
            if not smtp_use_ssl:
                server.starttls()
                server.ehlo()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_sender, [recipient_email], msg.as_string())
            server.quit()
            logger.info("Notificación de tarea enviada a %s.", recipient_email)
            return True
        except Exception:
            logger.exception("No se pudo enviar la notificación de tarea a %s.", recipient_email)
            return False
