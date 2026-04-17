# src/api/routes/feedback.py
"""
POST /alerts/{alert_id}/feedback  — operator TP/FP label
GET  /thresholds                  — inspect all per-zone θᵢ values (debug/demo)
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.api.database import get_conn
from src.api.threshold import update_theta, get_all_thresholds

router = APIRouter()


class FeedbackRequest(BaseModel):
    label:   str          # "TP" or "FP"
    user_id: str = "demo"


@router.post("/alerts/{alert_id}/feedback")
async def submit_feedback(alert_id: int, req: FeedbackRequest):
    """
    Mark an alert as True Positive or False Positive.
    Instantly recalibrates θᵢ for that zone — O(1), no model retraining.
    """
    if req.label not in ("TP", "FP"):
        raise HTTPException(status_code=422, detail="label must be 'TP' or 'FP'")

    # 1. Verify alert exists and get region_id
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(
        "SELECT region_id, score, theta_used FROM alerts WHERE alert_id = %s",
        (alert_id,)
    )
    row = cur.fetchone()
    if row is None:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    region_id, score, theta_used = row

    # 2. Log feedback to audit table
    cur.execute(
        """INSERT INTO alert_feedback (alert_id, region_id, label, user_id)
           VALUES (%s, %s, %s, %s)""",
        (alert_id, region_id, req.label, req.user_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    # 3. Run online θᵢ recalibration (pure logic in threshold.py)
    result = update_theta(region_id, req.label)

    return JSONResponse(content={
        "alert_id":     alert_id,
        "region_id":    region_id,
        "score":        score,
        **result,                        # theta_before, theta_after, reason, etc.
        "message": (
            f"Threshold {'raised' if result['theta_after'] > result['theta_before'] else 'lowered' if result['theta_after'] < result['theta_before'] else 'unchanged'} "
            f"for {region_id}: {result['theta_before']} → {result['theta_after']}"
        )
    })


@router.get("/thresholds")
async def get_thresholds():
    """
    Return all per-zone θᵢ values.
    Use this for the demo: watch θᵢ change live after clicking False Alarm.
    """
    thresholds = get_all_thresholds()
    return JSONResponse(content={
        "count":      len(thresholds),
        "thresholds": thresholds
    })
