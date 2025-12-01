import psycopg

try:
    conn = psycopg.connect(
        host='localhost',
        port='5432',
        database='---',  # Change to your actual DB name
        user='postgres',
        password='---'  # Your actual password
    )
    print("[SUCCESS] Connected successfully!")
    conn.close()
except Exception as e:
    print(f"[ERROR] Connection failed: {e}")