import os
import logging
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection pool
connection_pool = None

def get_db_connection():
    """Get database connection from pool"""
    global connection_pool
    
    if connection_pool is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        
        # Create connection pool
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 10,  # min and max connections
            database_url
        )
        logger.info("✅ Database connection pool created")
    
    return connection_pool.getconn()

def return_db_connection(conn):
    """Return connection to pool"""
    global connection_pool
    if connection_pool:
        connection_pool.putconn(conn)

@contextmanager
def get_db_cursor():
    """Context manager for database operations"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        cursor.close()
        return_db_connection(conn)

def setup_database():
    """Create tables if they don't exist"""
    logger.info("🗄️ Setting up database tables...")
    
    try:
        with get_db_cursor() as cursor:
            # Drop old table if it exists (fresh start)
            logger.info("🗑️ Dropping old table if exists...")
            cursor.execute("DROP TABLE IF EXISTS user_facts CASCADE")
            
            # Create user_facts table
            logger.info("📝 Creating new user_facts table...")
            cursor.execute("""
                CREATE TABLE user_facts (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chat_id, key)
                )
            """)
            
            # Create index on chat_id for faster lookups
            logger.info("🔍 Creating index...")
            cursor.execute("""
                CREATE INDEX idx_user_facts_chat_id 
                ON user_facts(chat_id)
            """)
            
            logger.info("✅ Memory table verified/created")
            
    except Exception as e:
        logger.error(f"❌ Error setting up database: {e}")
        raise

def save_fact(chat_id: int, key: str, value: str):
    """Save or update a user fact"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_facts (chat_id, key, value, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (chat_id, key) 
                DO UPDATE SET 
                    value = EXCLUDED.value,
                    updated_at = CURRENT_TIMESTAMP
            """, (chat_id, key, value))
            
            logger.info(f"💾 Saved fact: {key} for chat {chat_id}")
            
    except Exception as e:
        logger.error(f"❌ Error saving fact: {e}")
        raise

def get_fact(chat_id: int, key: str) -> str:
    """Get a specific user fact"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT value FROM user_facts 
                WHERE chat_id = %s AND key = %s
            """, (chat_id, key))
            
            result = cursor.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        logger.error(f"❌ Error getting fact: {e}")
        return None

def get_all_facts(chat_id: int) -> dict:
    """Get all facts for a user"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT key, value FROM user_facts 
                WHERE chat_id = %s
                ORDER BY updated_at DESC
            """, (chat_id,))
            
            results = cursor.fetchall()
            return {row[0]: row[1] for row in results}
            
    except Exception as e:
        logger.error(f"❌ Error getting all facts: {e}")
        return {}

def delete_fact(chat_id: int, key: str):
    """Delete a specific user fact"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                DELETE FROM user_facts 
                WHERE chat_id = %s AND key = %s
            """, (chat_id, key))
            
            logger.info(f"🗑️ Deleted fact: {key} for chat {chat_id}")
            
    except Exception as e:
        logger.error(f"❌ Error deleting fact: {e}")
        raise

def clear_all_facts(chat_id: int):
    """Clear all facts for a user"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                DELETE FROM user_facts 
                WHERE chat_id = %s
            """, (chat_id,))
            
            logger.info(f"🧹 Cleared all facts for chat {chat_id}")
            
    except Exception as e:
        logger.error(f"❌ Error clearing facts: {e}")
        raise
