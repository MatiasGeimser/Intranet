import psycopg2
from psycopg2 import errors
import random
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN birth_date TIMESTAMP;")
        print("Columna 'birth_date' agregada a PostgreSQL.")
    except errors.DuplicateColumn:
        print("La columna 'birth_date' ya existe.")
    except Exception as e:
        print(f"Error alterando la tabla: {e}")
    
    # Agregar mock data
    try:
        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()
        
        current_year = datetime.now().year
        current_month = datetime.now().month

        for (user_id,) in users:
            if random.random() > 0.5:
                if random.random() < 0.3:
                    month = current_month
                    day = random.randint(1, 28)
                else:
                    month = random.randint(1, 12)
                    day = random.randint(1, 28)
                
                year = random.randint(1970, 2000)
                birth_date_str = f"{year}-{month:02d}-{day:02d} 00:00:00"
                
                cursor.execute("UPDATE users SET birth_date = %s WHERE id = %s", (birth_date_str, user_id))

        print(f"Base de datos PostgreSQL actualizada. Procesados {len(users)} usuarios con cumpleaños mock.")
    except Exception as e:
        print(f"Error actualizando usuarios: {e}")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    main()
