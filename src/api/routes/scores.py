# src/api/routes/scores.py
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from src.api.scorer import get_scores_for_date, get_top_zones, get_available_dates
from datetime import date as DateType

router = APIRouter()


@router.get("/dates")
async def get_dates():
    dates = get_available_dates()
    return JSONResponse(content={
        "dates": dates,
        "count": len(dates),
        "first": dates[0]  if dates else None,
        "last":  dates[-1] if dates else None,
    })


@router.get("/scores")
async def get_scores(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    try:
        DateType.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date. Use YYYY-MM-DD.")

    # scorer.py handles in-memory caching — no DB round-trip needed
    scores    = get_scores_for_date(date)
    top_zones = get_top_zones(scores)

    return JSONResponse(content={
        "date":      date,
        "scores":    scores,
        "top_zones": top_zones,
        "source":    "gnn_csv",
    })
