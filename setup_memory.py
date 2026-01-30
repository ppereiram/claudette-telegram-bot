import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

def setup_memory_table():
    """Create user_facts table for persistent memory"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Create table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_facts (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                fact_key VARCHAR(255) NOT NULL,
                fact_value TEXT NOT NULL,
                category VARCHAR(100) DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, fact_key)
            )
        """)
        
        # Create index for faster searches
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_facts_key 
            ON user_facts(user_id, fact_key)
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Memory table created successfully")
        
    except Exception as e:
        print(f"❌ Error creating memory table: {e}")

if __name__ == "__main__":
    setup_memory_table()
