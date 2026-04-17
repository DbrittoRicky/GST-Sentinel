# src/api/ingest.py
"""
Daily score ingestion: reads scores/YYYY-MM-DD.csv → writes to alerts table.

Run manually:
    python -m src.api.ingest --date 2024-03-15

Or call ingest_date(date_str) programmatically from a scheduler / startup hook.

CSV columns expected (from src/model/score.py):
    region_id, score, chl_z, persistence_days, alert  (alert col is optional)
"""

import argparse
import pandas as pd
from pathlib import Path
from src.api.database import get_conn
from src.api.threshold import get_theta

REPO_ROOT  = Path(__file__).resolve().parents[2]
SCORES_DIR = REPO_ROOT / "data" / "processed" / "scores"


def ingest_date(date_str: str) -> dict:
    """
    Load scores CSV for date_str, compare each zone score vs θᵢ,
    insert qualifying zones into alerts table.

    Returns a summary dict: { ingested, skipped, total }
    """
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
    id_col    = "region_id"    if "region_id"         in df.columns else df.columns[0]
    score_col = "score"        if "score"             in df.columns else "chl_z"
    chlz_col  = "chl_z"        if "chl_z"             in df.columns else None
    pers_col  = "persistence_days" if "persistence_days" in df.columns else None

    conn = get_conn()
    cur  = conn.cursor()

    ingested = 0
    skipped  = 0

    for _, row in df.iterrows():
        region_id = str(row[id_col])
        score     = float(row[score_col])
        chl_z     = float(row[chlz_col])     if chlz_col and pd.notna(row[chlz_col])  else None
        pers_days = int(row[pers_col])        if pers_col and pd.notna(row[pers_col])  else 1

        # Fetch current θᵢ for this zone (inserts default row if zone is new)
        theta = get_theta(region_id)

        if score < theta:
            skipped += 1
            continue                          # below threshold — not an alert

        # Upsert: update score/theta if same zone+date already exists
        cur.execute(
            """INSERT INTO alerts
                   (region_id, alert_date, score, theta_used, chl_z, persistence_days)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (region_id, alert_date)
               DO UPDATE SET
                   score            = EXCLUDED.score,
                   theta_used       = EXCLUDED.theta_used,
                   chl_z            = EXCLUDED.chl_z,
                   persistence_days = EXCLUDED.persistence_days,
                   created_at       = NOW()""",
            (region_id, date_str, score, theta, chl_z, pers_days)
        )
        ingested += 1

    conn.commit()
    cur.close()
    conn.close()

    total = ingested + skipped
    print(f"[ingest] {date_str} → {ingested} alerts written, {skipped} below threshold (total zones: {total})")
    return {"date": date_str, "ingested": ingested, "skipped": skipped, "total": total}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest GNN scores into alerts table")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    args = parser.parse_args()
    result = ingest_date(args.date)
    print(result)
