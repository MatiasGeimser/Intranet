import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.task import DailyTaskConfig, Task
from app.models.user import User
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()

    def start(self):
        # Programar la verificación de tareas diarias para que corra cada minuto
        self.scheduler.add_job(
            self.check_daily_tasks,
            IntervalTrigger(minutes=1),
            id='check_daily_tasks_job',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("====== SCHEDULER INICIADO: Verificando tareas diarias cada minuto ======")

    def stop(self):
        self.scheduler.shutdown()
        logger.info("====== SCHEDULER DETENIDO ======")

    def check_daily_tasks(self):
        """Verifica y ejecuta las tareas diarias si coinciden con la hora actual."""
        db: Session = SessionLocal()
        try:
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")
            
            # Obtener tareas activas cuyo horario coincida con la hora actual
            daily_configs = db.query(DailyTaskConfig).filter(
                DailyTaskConfig.is_active == True,
                DailyTaskConfig.schedule_time == current_time_str
            ).all()

            for config in daily_configs:
                # Verificar si ya se ejecutó hoy
                if config.last_triggered_date and config.last_triggered_date.date() >= now.date():
                    continue

                # 1. Crear la Tarea real en el tablero
                new_task = Task(
                    title=config.title,
                    description=config.description,
                    status="todo",
                    created_by_id=config.created_by_id,
                    assigned_to_user_id=config.assigned_to_user_id,
                    daily_task_config_id=config.id
                )
                db.add(new_task)
                
                # 2. Actualizar fecha de ejecución
                config.last_triggered_date = now

                # 3. Enviar correo de recordatorio
                recipient = db.query(User).filter(User.id == config.assigned_to_user_id).first()
                creator = db.query(User).filter(User.id == config.created_by_id).first()
                if recipient:
                    try:
                        EmailService.send_task_assigned_email(
                            recipient_email=recipient.email,
                            recipient_name=recipient.full_name,
                            task_title=f"[Diaria] {config.title}",
                            assigner_name=creator.full_name if creator else "Sistema (Automático)",
                            note_title="Rutina Diaria"
                        )
                    except Exception as e:
                        logger.error(f"Error al enviar correo de tarea diaria a {recipient.email}: {e}")

                db.commit()
                logger.info(f"====== TAREA DIARIA GENERADA Y CORREO ENVIADO: '{config.title}' ======")
                
        except Exception as e:
            db.rollback()
            logger.error(f"Error en el worker de tareas diarias: {e}")
        finally:
            db.close()

# Instancia global (singleton)
scheduler_service = SchedulerService()
