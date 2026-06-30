import asyncio
import subprocess
from app.core.database import SessionLocal
from app.models.it_asset import ITAsset
from app.api.endpoints.inventory_map import broadcast_status
from datetime import datetime, timezone

async def ping_ip(ip: str) -> bool:
    if not ip:
        return False
    # Asumimos entorno Windows basado en la petición del usuario
    try:
        # ping -n 1 (1 paquete) -w 1000 (timeout 1000ms)
        process = await asyncio.create_subprocess_exec(
            'ping', '-n', '1', '-w', '1000', ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        # En Windows, un ping fallido a veces devuelve exit code 0 pero dice "Host de destino inaccesible"
        output = stdout.decode('cp850', errors='ignore').lower()
        if process.returncode == 0 and "inaccesible" not in output and "unreachable" not in output and "agotado" not in output and "timed out" not in output:
            return True
        return False
    except Exception as e:
        print(f"Error pinging {ip}: {e}")
        return False

async def monitor_assets():
    while True:
        db = SessionLocal()
        try:
            # Obtener activos con IP asignada
            activos = db.query(ITAsset).filter(ITAsset.ip_address != None, ITAsset.ip_address != '').all()
            
            changes = []
            for activo in activos:
                is_online = await ping_ip(activo.ip_address)
                new_status = "Activo" if is_online else "Fuera de Linea"
                
                # Si cambió de estado o no tenía estado previo
                if activo.status != new_status:
                    activo.status = new_status
                    activo.last_ping_at = datetime.now(timezone.utc)
                    changes.append({
                        "id": activo.id,
                        "hostname": activo.name,
                        "ip": activo.ip_address,
                        "status": new_status
                    })
                # Si está online, actualizamos el último ping
                elif is_online:
                    activo.last_ping_at = datetime.now(timezone.utc)
                    
            if changes:
                db.commit()
                # Enviar a WebSockets
                await broadcast_status({"type": "status_update", "changes": changes})
                
        except Exception as e:
            print(f"Error in ping_service: {e}")
        finally:
            db.close()
            
        # Esperar 30 segundos antes de la siguiente ronda
        await asyncio.sleep(30)
