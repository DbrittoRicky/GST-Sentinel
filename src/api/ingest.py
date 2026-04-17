# src/api/ingest.py
import argparse
import pandas as pd
from pathlib import Path
from src.api.database import get_conn, release_conn

REPO_ROOT  = Path(__file__).resolve().parents[2]
SCORES_DIR = REPO_ROOT / "data" / "processed" / "scores"
THETA_DEFAULT = 2.0


def _load_all_thetas(conn) -> dict:
    """Bulk fetch all θᵢ values in one query. Returns { region_id: theta }."""
    cur = conn.cursor()
    cur.execute("SELECT region_id, theta FROM region_thresholds")
    rows = cur.fetchall()
    cur.close()
    return {r[0]: r[1] for r in rows}


def _ensure_thetas(conn, region_ids: list, existing: dict):
    new_zones = [(zid, THETA_DEFAULT) for zid in region_ids if zid not in existing]
    if not new_zones:
        return
    from psycopg2.extras import execute_values
    cur = conn.cursor()
    execute_values(
        cur,
        """INSERT INTO region_thresholds (region_id, theta)
           VALUES %s
           ON CONFLICT DO NOTHING""",
        new_zones
    )
    conn.commit()
    cur.close()



def ingest_date(date_str: str) -> dict:
    # --- locate CSV ---
    csv_path = None
    for fmt in [f"scores_{date_str}.csv", f"scores{date_str}.csv", f"scores-{date_str}.csv"]:
        p = SCORES_DIR / fmt
        if p.exists():
            csv_path = p
            break

    if csv_path is None:
        print(f"[ingest] No CSV found for {date_str} in {SCORES_DIR}")
        return {"date": date_str, "ingested": 0, "skipped": 0, "total": 0, "error": "csv_not_found"}

    df = pd.read_csv(csv_path)

    # Normalise column names
    id_col    = "region_id"        if "region_id"         in df.columns else df.columns[0]
    score_col = "score"            if "score"             in df.columns else "chl_z"
    chlz_col  = "chl_z"            if "chl_z"             in df.columns else None
    pers_col  = "persistence_days" if "persistence_days"  in df.columns else None

    conn = get_conn()
    try:
        # 1. Bulk fetch existing thetas — ONE round-trip
        thetas = _load_all_thetas(conn)

        # 2. Bulk insert default rows for new zones — ONE round-trip
        region_ids = df[id_col].astype(str).tolist()
        _ensure_thetas(conn, region_ids, thetas)

        # Refresh thetas after insert
        thetas = _load_all_thetas(conn)

        # 3. Build alert rows in Python — zero DB calls
        alert_rows = []
        skipped    = 0

        for _, row in df.iterrows():
            region_id = str(row[id_col])
            score     = float(row[score_col])
            chl_z     = float(row[chlz_col])    if chlz_col and pd.notna(row.get(chlz_col)) else None
            pers_days = int(row[pers_col])       if pers_col and pd.notna(row.get(pers_col)) else 1
            theta     = thetas.get(region_id, THETA_DEFAULT)

            if score < theta:
                skipped += 1
                continue

            alert_rows.append((region_id, date_str, score, theta, chl_z, pers_days))

        # 4. Bulk upsert all alert rows — ONE round-trip
        if alert_rows:
            from psycopg2.extras import execute_values
            cur = conn.cursor()
            execute_values(
                cur,
                """INSERT INTO alerts (region_id, alert_date, score, theta_used, chl_z, persistence_days)
                   VALUES %s
                   ON CONFLICT (region_id, alert_date)
                   DO UPDATE SET
                       score            = EXCLUDED.score,
                       theta_used       = EXCLUDED.theta_used,
                       chl_z            = EXCLUDED.chl_z,
                       persistence_days = EXCLUDED.persistence_days,
                       created_at       = NOW()""",
                alert_rows
            )
            conn.commit()
            cur.close()

    finally:
        release_conn(conn)

    ingested = len(alert_rows)
    total    = ingested + skipped
    print(f"[ingest] {date_str} → {ingested} alerts written, {skipped} below threshold (total zones: {total})")
    return {"date": date_str, "ingested": ingested, "skipped": skipped, "total": total}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest GNN scores into alerts table")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    args = parser.parse_args()
    result = ingest_date(args.date)
    print(result)
