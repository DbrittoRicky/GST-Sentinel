# src/api/routes/scores.py
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from src.api.scorer import get_scores_for_date, get_top_zones
from src.api.database import get_conn
from datetime import date as DateType
import psycopg2

router = APIRouter()

@router.get("/scores")
async def get_scores(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    # Validate date format
    try:
        DateType.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Try PostgreSQL cache first
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT zone_id, z_score, chl_raw, mu FROM score_cache WHERE date = %s",
            (date,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if rows:
            scores = {r[0]: r[1] for r in rows}
            top_zones = get_top_zones(scores)
            return JSONResponse(content={"date": date, "scores": scores, "top_zones": top_zones})
    except Exception as e:
        print(f"DB cache miss ({e}), computing from tensor...")

    # Compute from tensor
    scores = get_scores_for_date(date)
    top_zones = get_top_zones(scores)

    # Write to DB cache asynchronously (best-effort)
    try:
        conn = get_conn()
        cur = conn.cursor()
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO score_cache (date, zone_id, z_score) VALUES %s ON CONFLICT DO NOTHING",
            [(date, zid, zscore) for zid, zscore in scores.items()]
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB write skipped: {e}")

    return JSONResponse(content={
        "date": date,
        "scores": scores,
        "top_zones": top_zones
    })