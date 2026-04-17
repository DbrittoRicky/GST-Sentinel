# src/api/database.py
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/sentinel_db")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS score_cache (
            date        DATE NOT NULL,
            zone_id     TEXT NOT NULL,
            z_score     FLOAT NOT NULL,
            chl_raw     FLOAT,
            mu          FLOAT,
            PRIMARY KEY (date, zone_id)
        );
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_score_date ON score_cache(date);
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("DB initialized: score_cache table ready.")