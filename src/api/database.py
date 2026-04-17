# src/api/database.py
import psycopg2
import psycopg2.pool
import os
from dotenv import load_dotenv

load_dotenv()

_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            dsn = "dbname={} user={} password={} host={} port={} sslmode=require".format(
                os.getenv("DB_NAME",     "neondb"),
                os.getenv("DB_USER",     "postgres"),
                os.getenv("DB_PASSWORD", ""),
                os.getenv("DB_HOST",     "localhost"),
                os.getenv("DB_PORT",     "5432"),
            )
        # Free tier: max 10 concurrent connections — keep pool small
        _pool = psycopg2.pool.ThreadedConnectionPool(1, 5, dsn)
        print("Neon DB pool initialised")
    return _pool

def get_conn():
    return _get_pool().getconn()

def release_conn(conn):
    _get_pool().putconn(conn)

def init_db():
    conn = get_conn()
    try:
        cur = conn.cursor()
        schema_path = os.path.join(os.path.dirname(__file__), "db", "schema.sql")
        cur.execute(open(schema_path).read())
        conn.commit()
        cur.close()
        print("Neon DB schema initialised.")
    finally:
        release_conn(conn)
