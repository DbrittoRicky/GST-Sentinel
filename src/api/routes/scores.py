
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from src.api.scorer import get_scores_for_date, get_top_zones, get_available_dates
from src.api.database import get_conn
from datetime import date as DateType
import psycopg2
import psycopg2.extras

router = APIRouter()

@router.get("/dates")
async def get_dates():
    """Return list of all available scored dates from GNN output."""
    dates = get_available_dates()
    return JSONResponse(content={
        "dates": dates,
        "count": len(dates),
        "first": dates[0] if dates else None,
        "last": dates[-1] if dates else None,
    })

@router.get("/scores")
async def get_scores(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    try:
        DateType.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date. Use YYYY-MM-DD.")

    # Try DB cache first
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT zone_id, z_score FROM score_cache WHERE date = %s",
            (date,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if rows:
            scores = {r[0]: r[1] for r in rows}
            return JSONResponse(content={
                "date": date,
                "scores": scores,
                "top_zones": get_top_zones(scores),
                "source": "cache"
            })
    except Exception as e:
        print(f"DB cache miss: {e}")

    # Load from GNN CSV
    scores = get_scores_for_date(date)
    top_zones = get_top_zones(scores)

    # Write to DB cache
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
        print(f"DB cache write skipped: {e}")

    return JSONResponse(content={
        "date": date,
        "scores": scores,
        "top_zones": top_zones,
        "source": "gnn_csv"
    })