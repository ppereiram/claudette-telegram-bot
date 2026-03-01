import psycopg2
url = "postgresql://claudette:OYWkEyUbE0oc0jfZc0p1owGqRTJMU8OI@dpg-d5u338kr85hc739t04sg-a.oregon-postgres.render.com/claudette?sslmode=require"
try:
    conn = psycopg2.connect(url)
    print("✅ Conexión exitosa!")
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")
