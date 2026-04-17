# src/api/routes/alerts.py
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from src.api.database import get_conn, release_conn
from datetime import date as DateType
import math

router = APIRouter()

RISK_LABELS = [
    (10.0, "CRITICAL"),
    (5.0,  "HIGH"),
    (2.0,  "ELEVATED"),
    (0.0,  "NORMAL"),
]

def _risk_label(score: float) -> str:
    for threshold, label in RISK_LABELS:
        if score >= threshold:
            return label
    return "NORMAL"

def _safe(val, digits=4):
    """Sanitize float — replace NaN/Inf with None for JSON safety."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, digits)
    except (TypeError, ValueError):
        return None


@router.get("/alerts")
async def get_alerts(
    date:  str = Query(..., description="Date in YYYY-MM-DD format"),
    top_k: int = Query(10,  ge=1, le=100),
):
    try:
        DateType.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                a.alert_id,
                a.region_id,
                a.score,
                a.theta_used,
                a.chl_z,
                a.persistence_days,
                COALESCE(r.theta, 2.0) AS current_theta
            FROM alerts a
            LEFT JOIN region_thresholds r ON a.region_id = r.region_id
            WHERE a.alert_date = %s
              AND a.score >= COALESCE(r.theta, a.theta_used)
            ORDER BY a.score DESC
            LIMIT %s
            """,
            (date, top_k)
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        release_conn(conn)

    alerts = []
    for r in rows:
        score = _safe(r[2])
        if score is None:
            continue                      # drop rows with unserializable scores
        alerts.append({
            "alert_id":         r[0],
            "region_id":        r[1],
            "score":            score,
            "theta_used":       _safe(r[3]),
            "chl_z":            _safe(r[4]),
            "persistence_days": r[5],
            "current_theta":    _safe(r[6]),
            "risk_label":       _risk_label(score),
        })

    return JSONResponse(content={
        "date":   date,
        "count":  len(alerts),
        "alerts": alerts,
    })


@router.get("/zones/{zone_id}/history")
async def get_zone_history(
    zone_id: str,
    days:    int = Query(30, ge=1, le=90),
):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT alert_date, score, chl_z, persistence_days, theta_used
            FROM alerts
            WHERE region_id = %s
            ORDER BY alert_date DESC
            LIMIT %s
            """,
            (zone_id, days)
        )
        rows = cur.fetchall()

        if not rows:
            cur.execute(
                """
                SELECT date, z_score, NULL, 0, 2.0
                FROM score_cache
                WHERE zone_id = %s
                ORDER BY date DESC
                LIMIT %s
                """,
                (zone_id, days)
            )
            rows = cur.fetchall()
        cur.close()
    finally:
        release_conn(conn)

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No history found for zone {zone_id}."
        )

    history = []
    for r in reversed(rows):
        score = _safe(r[1])
        if score is None:
            continue
        history.append({
            "date":             str(r[0]),
            "score":            score,
            "chl_z":            _safe(r[2]),
            "persistence_days": r[3],
            "theta_used":       _safe(r[4]),
            "risk_label":       _risk_label(score),
        })

    return JSONResponse(content={
        "zone_id": zone_id,
        "days":    days,
        "count":   len(history),
        "history": history,
    })
