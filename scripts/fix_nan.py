# scripts/fix_nan.py
from src.api.database import get_conn, release_conn

conn = get_conn()
cur  = conn.cursor()

cur.execute("SELECT COUNT(*) FROM alerts WHERE score = 'NaN'::float")
print('NaN score rows:', cur.fetchone()[0])

cur.execute("DELETE FROM alerts WHERE score = 'NaN'::float OR score IS NULL")
conn.commit()
print('Deleted NaN rows.')

cur.execute('SELECT COUNT(*) FROM alerts')
print('Remaining alerts:', cur.fetchone()[0])

cur.close()
release_conn(conn)
