import os
import logging
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection using psycopg3"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # psycopg3 usa connect() directamente
    return psycopg.connect(database_url)

def setup_database():
    """Setup database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create facts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id SERIAL PRIMARY KEY,
                fact_key VARCHAR(255) UNIQUE NOT NULL,
                fact_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("✅ Database setup complete")
        
    except Exception as e:
        logger.error(f"❌ Database setup error: {e}")
        raise

def save_fact(fact_key: str, fact_value: str) -> bool:
    """Save or update a fact"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO facts (fact_key, fact_value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (fact_key) 
            DO UPDATE SET 
                fact_value = EXCLUDED.fact_value,
                updated_at = CURRENT_TIMESTAMP
        """, (fact_key, fact_value))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error saving fact: {e}")
        return False

def get_fact(fact_key: str) -> str:
    """Get a fact by key"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT fact_value FROM facts WHERE fact_key = %s",
            (fact_key,)
        )
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result[0] if result else None
        
    except Exception as e:
        logger.error(f"Error getting fact: {e}")
        return None

def get_all_facts() -> dict:
    """Get all facts as a dictionary"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT fact_key, fact_value FROM facts ORDER BY updated_at DESC")
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {row[0]: row[1] for row in results}
        
    except Exception as e:
        logger.error(f"Error getting all facts: {e}")
        return {}
