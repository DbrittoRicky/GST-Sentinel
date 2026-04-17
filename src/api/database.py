# src/api/database.py
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    # psycopg2 accepts a full DSN string as first positional arg
    # Format: postgresql://user:password@host:port/dbname
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        # Fallback: build from individual env vars
        dsn = "dbname={} user={} password={} host={} port={}".format(
            os.getenv("DB_NAME", "sentinel_db"),
            os.getenv("DB_USER", "postgres"),
            os.getenv("DB_PASSWORD", "postgres"),
            os.getenv("DB_HOST", "127.0.0.1"),
            os.getenv("DB_PORT", "5432"),
        )
    return psycopg2.connect(dsn)  # pass as positional arg, NOT keyword arg

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    schema_path = os.path.join(os.path.dirname(__file__), "db", "schema.sql")
    cur.execute(open(schema_path).read())
    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized.")