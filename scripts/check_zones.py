# scripts/check_zones.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.database import get_conn, release_conn

conn = get_conn()
cur  = conn.cursor()

# Check if IN-R2027 exists
cur.execute("SELECT region_id, alert_date, score FROM alerts WHERE region_id='IN-R2027' LIMIT 5")
print("IN-R2027 rows:", cur.fetchall())

# Get top 3 real zones by score
cur.execute("SELECT region_id, alert_date, score FROM alerts ORDER BY score DESC LIMIT 3")
print("Top 3 zones:", cur.fetchall())

cur.close()
release_conn(conn)
