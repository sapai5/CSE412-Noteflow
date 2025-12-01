import psycopg

try:
    conn = psycopg.connect(
        host='localhost',
        port='5432',
        dbname=YOUR_DB
        user='postgres',
        password=YOUR_PASSWORD
    )
    conn.autocommit = True  
    cur = conn.cursor()
    
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'notetaker'")
    exists = cur.fetchone()
    
    if not exists:
        cur.execute("CREATE DATABASE notetaker")
        print("[SUCCESS] Database 'notetaker' created successfully!")
    else:
        print("[INFO] Database 'notetaker' already exists")
    
    cur.close()
    conn.close()
    
    print("\n[INFO] Loading schema...")
    conn = psycopg.connect(
        host='localhost',
        port='5432',
        dbname=YOUR_DB
        user='postgres',
        password=YOUR_PASSWORD
    )
    cur = conn.cursor()
    
    with open('schema.sql', 'r', encoding='utf-8') as f:
        schema = f.read()
    
    cur.execute(schema)
    conn.commit()
    
    print("[SUCCESS] Schema loaded successfully")
    
    cur.close()
    conn.close()
    
    print("\n[SUCCESS] Database setup complete, run: python app.py")
    
except Exception as e:
    print(f"[ERROR] Setup failed: {e}")
