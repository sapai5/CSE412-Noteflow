import psycopg2

try:
    conn = psycopg2.connect(
        host='localhost',
        port='5432',
        database='---',  # Change to your actual DB name
        user='postgres',
        password='---'  # Your actual password
    )
    print("✅ Connected successfully!")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")