import sqlite3
import os
from sqlalchemy import create_engine, MetaData, text
from dotenv import load_dotenv

load_dotenv()

def inspect_databases():
    print("--- SQLITE LOCAL ---")
    local_conn = sqlite3.connect('intranet.db')
    local_cur = local_conn.cursor()
    local_cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in local_cur.fetchall()]
    
    for table in sorted(tables):
        if table.startswith('sqlite_'):
            continue
        local_cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = local_cur.fetchone()[0]
        print(f"Table '{table}': {count} records")
    local_conn.close()

    print("\n--- SUPABASE REMOTE ---")
    supabase_url = os.getenv("DATABASE_URL")
    if not supabase_url:
        print("DATABASE_URL not found in environment!")
        return
        
    engine = create_engine(supabase_url)
    with engine.connect() as conn:
        # Get all table names in public schema
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """))
        supabase_tables = [row[0] for row in result.fetchall()]
        
        for table in sorted(supabase_tables):
            try:
                res = conn.execute(text(f"SELECT COUNT(*) FROM \"{table}\""))
                count = res.fetchone()[0]
                print(f"Table '{table}': {count} records")
            except Exception as e:
                print(f"Error querying table '{table}': {e}")

if __name__ == "__main__":
    inspect_databases()
