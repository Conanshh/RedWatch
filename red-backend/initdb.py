import os
import psycopg2
import logging

def setup_database():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Error: No se encontró DATABASE_URL")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Creamos la tabla
        cur.execute('''
            CREATE TABLE IF NOT EXISTS favoritos (
                user_id BIGINT,
                alias TEXT,
                paradero_id TEXT,
                PRIMARY KEY (user_id, alias)
            );
        ''')
        
        conn.commit()
        print("✅ Tabla 'favoritos' verificada/creada con éxito en Neon.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error al inicializar DB: {e}")

if __name__ == "__main__":
    setup_database()