import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
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

        # Verificar si SMTP está configurado
        smtp_user = settings.SMTP_USER
        smtp_password = settings.SMTP_PASSWORD
        smtp_host = settings.SMTP_HOST
        smtp_port = settings.SMTP_PORT
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

            part = MIMEText(html_content, "html")
            msg.attach(part)

            # Enviar por SMTP
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.ehlo()
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
