import os
import psycopg2
import logging
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

# Configurar logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("❌ [DB] No se encontró DATABASE_URL en las variables de entorno.")
        return

    try:
        logger.info("🗄️ [DB] Intentando conectar a Neon...")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        logger.info("🔨 [DB] Verificando tabla 'favoritos'...")
        cur.execute('''
            CREATE TABLE IF NOT EXISTS favoritos (
                user_id BIGINT,
                alias TEXT,
                paradero_id TEXT,
                PRIMARY KEY (user_id, alias)
            );
        ''')
        
        conn.commit()
        logger.info("✅ [DB] Tabla 'favoritos' lista para usar.")
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"❌ [DB] Fallo al inicializar: {e}")

if __name__ == "__main__":
    setup_database()