# src/api/database.py
import psycopg2
import psycopg2.pool
import os
from dotenv import load_dotenv

load_dotenv()

_pool = None


def _build_dsn() -> str:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        dsn = "dbname={} user={} password={} host={} port={} sslmode=require".format(
            os.getenv("DB_NAME",     "neondb"),
            os.getenv("DB_USER",     "postgres"),
            os.getenv("DB_PASSWORD", ""),
            os.getenv("DB_HOST",     "localhost"),
            os.getenv("DB_PORT",     "5432"),
        )
    return dsn


def _make_pool():
    return psycopg2.pool.ThreadedConnectionPool(
        1, 5,
        _build_dsn(),
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
    )


def _get_pool():
    global _pool
    if _pool is None:
        _pool = _make_pool()
        print("Neon DB pool initialised")
    return _pool


def get_conn():
    """Get a live connection. Retries once on stale SSL / Neon cold-start."""
    global _pool
    try:
        conn = _get_pool().getconn()
        conn.cursor().execute("SELECT 1")   # lightweight liveness ping
        return conn
    except Exception:
        # Stale pool — rebuild and try once more
        print("[db] Stale connection detected — rebuilding pool...")
        try:
            if _pool:
                _pool.closeall()
        except Exception:
            pass
        _pool = _make_pool()
        return _pool.getconn()


def release_conn(conn):
    try:
        _get_pool().putconn(conn)
    except Exception:
        pass


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
