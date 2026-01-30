import os
import psycopg2

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in environment variables")
    exit(1)

# Fix PostgreSQL connection string if needed
# Render uses postgresql:// but psycopg2 needs postgres://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgres://", 1)

def setup_memory_table():
    """Create user_facts table for persistent memory"""
    try:
        print(f"🔌 Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        
        print("📋 Creating user_facts table...")
        
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
        
        print("📊 Creating index...")
        
        # Create index for faster searches
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_facts_key 
            ON user_facts(user_id, fact_key)
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ Memory table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating memory table: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    setup_memory_table()
