import sqlite3
import random
from datetime import datetime, timedelta

def main():
    db_path = 'intranet.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Agregar la columna birth_date si no existe
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN birth_date DATETIME")
        print("Columna 'birth_date' agregada exitosamente.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("La columna 'birth_date' ya existe. Omitiendo ALTER TABLE.")
        else:
            raise e

    # 2. Generar fechas de cumpleaños de prueba (mock data)
    # Seleccionaremos algunos usuarios para asignarles cumpleaños este mes
    cursor.execute("SELECT id FROM users")
    users = cursor.fetchall()
    
    current_year = datetime.now().year
    current_month = datetime.now().month

    for (user_id,) in users:
        # 50% de probabilidad de tener un cumpleaños asignado
        if random.random() > 0.5:
            # 30% de los que tienen cumpleaños cumplen en este mes (para pruebas)
            if random.random() < 0.3:
                month = current_month
                day = random.randint(1, 28)
            else:
                month = random.randint(1, 12)
                day = random.randint(1, 28)
            
            # Año de nacimiento aleatorio entre 1970 y 2000
            year = random.randint(1970, 2000)
            birth_date_str = f"{year}-{month:02d}-{day:02d} 00:00:00.000000"
            
            cursor.execute("UPDATE users SET birth_date = ? WHERE id = ?", (birth_date_str, user_id))

    conn.commit()
    print(f"Base de datos actualizada. Se agregaron cumpleaños mock a {len(users)} usuarios (algunos vacíos).")
    conn.close()

if __name__ == '__main__':
    main()
