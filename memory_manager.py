"""
Memory Manager para Claudette Bot.
Usa PostgreSQL (claudette-db en Render) como almacenamiento persistente.
Fallback a JSON local si no hay DATABASE_URL (desarrollo local).
"""

import json
import os
import logging

logger = logging.getLogger("claudette")

# --- Intentar conectar a PostgreSQL ---
_use_postgres = False
_pg_conn_string = None

try:
    from config import DATABASE_URL
    if DATABASE_URL:
        import psycopg2
        _pg_conn_string = DATABASE_URL
        _use_postgres = True
        logger.info("🗄️ Memoria: PostgreSQL (claudette-db)")
    else:
        logger.info("🗄️ Memoria: JSON local (no hay DATABASE_URL)")
except ImportError:
    logger.warning("🗄️ Memoria: JSON local (psycopg2 no instalado)")
except Exception as e:
    logger.warning(f"🗄️ Memoria: JSON local (error: {e})")


# =====================================================
# POSTGRESQL BACKEND
# =====================================================

def _pg_connect():
    """Crea conexion a PostgreSQL."""
    import psycopg2
    return psycopg2.connect(_pg_conn_string)


def _pg_setup():
    """Crea tabla si no existe."""
    try:
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_memory (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("🗄️ Tabla user_memory verificada/creada")
        return True
    except Exception as e:
        logger.error(f"Error creando tabla user_memory: {e}")
        return False


# --- AUTO-CREAR TABLA al detectar PostgreSQL ---
_table_ready = False
if _use_postgres:
    _table_ready = _pg_setup()
    # Migrar datos de JSON si existen
    if _table_ready and os.path.exists('user_memory.json'):
        try:
            with open('user_memory.json', 'r') as f:
                json_data = json.load(f)
            if json_data:
                logger.info(f"🔄 Migrando {len(json_data)} facts de JSON a PostgreSQL...")
                conn = _pg_connect()
                cur = conn.cursor()
                for k, v in json_data.items():
                    cur.execute("""
                        INSERT INTO user_memory (key, value, updated_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                    """, (k, str(v)))
                conn.commit()
                cur.close()
                conn.close()
                os.rename('user_memory.json', 'user_memory.json.migrated')
                logger.info("✅ Migración completa. JSON respaldado.")
        except Exception as e:
            logger.error(f"Error migrando JSON: {e}")


def _pg_get_all():
    """Lee todos los facts desde PostgreSQL."""
    try:
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM user_memory")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {row[0]: row[1] for row in rows}
    except Exception as e:
        logger.error(f"PG get_all error: {e}")
        return {}


def _pg_save(key, value):
    """Guarda o actualiza un fact en PostgreSQL."""
    try:
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_memory (key, value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (key)
            DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
        """, (key, str(value)))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"PG save error: {e}")
        return False


def _pg_get(key):
    """Lee un fact especifico desde PostgreSQL."""
    try:
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute("SELECT value FROM user_memory WHERE key = %s", (key,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"PG get error: {e}")
        return None


def _pg_delete(key):
    """Elimina un fact de PostgreSQL."""
    try:
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM user_memory WHERE key = %s", (key,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"PG delete error: {e}")
        return False


# =====================================================
# JSON FALLBACK (desarrollo local)
# =====================================================

MEMORY_FILE = 'user_memory.json'


def _json_load():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando JSON: {e}")
    return {}


def _json_save_all(data):
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando JSON: {e}")


# =====================================================
# API PUBLICA (La que usan brain.py y tools_registry.py)
# =====================================================

def setup_database():
    """Compatibilidad — la tabla ya se crea automaticamente al importar."""
    pass


def get_all_facts():
    """Devuelve todo lo que el bot recuerda como un diccionario."""
    if _use_postgres:
        return _pg_get_all()
    return _json_load()


def save_fact(key, value):
    """Guarda un dato nuevo."""
    if _use_postgres:
        return _pg_save(key, value)
    data = _json_load()
    data[key] = value
    _json_save_all(data)
    return True


def get_fact(key):
    """Recupera un dato especifico."""
    if _use_postgres:
        return _pg_get(key)
    data = _json_load()
    return data.get(key)


def delete_fact(key):
    """Elimina un dato."""
    if _use_postgres:
        return _pg_delete(key)
    data = _json_load()
    if key in data:
        del data[key]
        _json_save_all(data)
    return True
