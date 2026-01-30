import os
import psycopg2
import logging
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

def save_user_fact(user_id, key, value, category="general"):
    """
    Save a fact to user's persistent memory
    
    Args:
        user_id: Telegram chat ID
        key: Identifier for the fact (e.g., "pasaporte_sofia", "cumpleaños_liliana")
        value: The actual data
        category: Category for organization (e.g., "familia", "salud", "trabajo")
    
    Returns:
        bool: True if saved successfully
    """
    if not DATABASE_URL:
        logging.error("DATABASE_URL not configured")
        return False
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Upsert: Insert or update if key exists
        cur.execute("""
            INSERT INTO user_facts (user_id, fact_key, fact_value, category, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, fact_key) 
            DO UPDATE SET 
                fact_value = EXCLUDED.fact_value,
                category = EXCLUDED.category,
                updated_at = EXCLUDED.updated_at
        """, (str(user_id), key, value, category, datetime.now()))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logging.info(f"✅ Saved fact: {key} = {value}")
        return True
        
    except Exception as e:
        logging.error(f"Error saving fact: {e}")
        return False

def get_user_fact(user_id, query):
    """
    Retrieve a fact from user's memory
    
    Args:
        user_id: Telegram chat ID
        query: Search term (searches in fact_key and fact_value)
    
    Returns:
        str: The fact value, or None if not found
    """
    if not DATABASE_URL:
        return None
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Search by key or value
        cur.execute("""
            SELECT fact_key, fact_value, category 
            FROM user_facts 
            WHERE user_id = %s 
            AND (fact_key ILIKE %s OR fact_value ILIKE %s)
            ORDER BY updated_at DESC
            LIMIT 5
        """, (str(user_id), f"%{query}%", f"%{query}%"))
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        if not results:
            return None
        
        # Format results
        if len(results) == 1:
            return results[0][1]  # Just return the value
        else:
            # Multiple results - return formatted
            formatted = []
            for key, value, category in results:
                formatted.append(f"• {key}: {value} ({category})")
            return "\n".join(formatted)
        
    except Exception as e:
        logging.error(f"Error retrieving fact: {e}")
        return None

def get_all_user_facts(user_id, category=None):
    """Get all facts for a user, optionally filtered by category"""
    if not DATABASE_URL:
        return []
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        if category:
            cur.execute("""
                SELECT fact_key, fact_value, category 
                FROM user_facts 
                WHERE user_id = %s AND category = %s
                ORDER BY updated_at DESC
            """, (str(user_id), category))
        else:
            cur.execute("""
                SELECT fact_key, fact_value, category 
                FROM user_facts 
                WHERE user_id = %s
                ORDER BY category, updated_at DESC
            """, (str(user_id),))
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        return results
        
    except Exception as e:
        logging.error(f"Error getting all facts: {e}")
        return []

def delete_user_fact(user_id, key):
    """Delete a specific fact"""
    if not DATABASE_URL:
        return False
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("""
            DELETE FROM user_facts 
            WHERE user_id = %s AND fact_key = %s
        """, (str(user_id), key))
        
        deleted = cur.rowcount > 0
        conn.commit()
        cur.close()
        conn.close()
        
        return deleted
        
    except Exception as e:
        logging.error(f"Error deleting fact: {e}")
        return False
