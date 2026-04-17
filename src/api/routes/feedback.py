# src/api/routes/feedback.py
"""
POST /alerts/{alert_id}/feedback  — operator TP/FP label
GET  /thresholds                  — inspect all per-zone θᵢ values (debug/demo)
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.api.database import get_conn, release_conn
from src.api.threshold import update_theta, get_all_thresholds

router = APIRouter()


class FeedbackRequest(BaseModel):
    label:   str
    user_id: str = "demo"


@router.post("/alerts/{alert_id}/feedback")
async def submit_feedback(alert_id: int, req: FeedbackRequest):
    if req.label not in ("TP", "FP"):
        raise HTTPException(status_code=422, detail="label must be 'TP' or 'FP'")

    # 1. Verify alert exists and get region_id — resolve before try/finally
    region_id = None
    score     = None

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT region_id, score, theta_used FROM alerts WHERE alert_id = %s",
            (alert_id,)
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        region_id, score, _ = row

        # 2. Log feedback to audit table
        cur.execute(
            """INSERT INTO alert_feedback (alert_id, region_id, label, user_id)
               VALUES (%s, %s, %s, %s)""",
            (alert_id, region_id, req.label, req.user_id)
        )
        conn.commit()
        cur.close()
    finally:
        release_conn(conn)

    # 3. Online θᵢ recalibration — runs AFTER connection is returned to pool
    result = update_theta(region_id, req.label)

    direction = (
        "raised"     if result["theta_after"] > result["theta_before"] else
        "lowered"    if result["theta_after"] < result["theta_before"] else
        "unchanged"
    )

    return JSONResponse(content={
        "alert_id":  alert_id,
        "region_id": region_id,
        "score":     score,
        **result,
        "message": f"Threshold {direction} for {region_id}: {result['theta_before']} → {result['theta_after']}"
    })


@router.get("/thresholds")
async def get_thresholds():
    thresholds = get_all_thresholds()
    return JSONResponse(content={
        "count":      len(thresholds),
        "thresholds": thresholds
    })
