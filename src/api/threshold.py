# src/api/threshold.py
"""
Online per-zone threshold recalibration.

Rule (from spec):
    Pᵢ = TPᵢ / (TPᵢ + FPᵢ)
    If Pᵢ < 0.30  →  θᵢ += DELTA_UP    (too many FPs → raise bar)
    If Pᵢ > 0.70 and volume < MIN_VOL  →  θᵢ -= DELTA_DOWN  (too strict → lower bar)
    Clamp θᵢ ∈ [THETA_MIN, THETA_MAX]

All DB operations use raw psycopg2 via get_conn() — no ORM.
"""

from src.api.database import get_conn

THETA_DEFAULT = 2.0
THETA_MIN     = 1.5
THETA_MAX     = 4.0
DELTA_UP      = 0.2   # raise threshold when too many FPs
DELTA_DOWN    = 0.1   # lower threshold when too strict
MIN_VOL       = 5     # minimum feedback count before lowering threshold


def get_theta(region_id: str) -> float:
    """Return current θᵢ for a zone. Inserts default row if zone is new."""
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(
        "SELECT theta FROM region_thresholds WHERE region_id = %s",
        (region_id,)
    )
    row = cur.fetchone()
    if row is None:
        cur.execute(
            """INSERT INTO region_thresholds (region_id, theta, tp_count, fp_count)
               VALUES (%s, %s, 0, 0)
               ON CONFLICT (region_id) DO NOTHING""",
            (region_id, THETA_DEFAULT)
        )
        conn.commit()
        theta = THETA_DEFAULT
    else:
        theta = row[0]
    cur.close()
    conn.close()
    return theta


def update_theta(region_id: str, label: str) -> dict:
    """
    Apply one TP or FP feedback event and recalibrate θᵢ.

    Returns a dict with before/after state for logging and API response.
    label must be 'TP' or 'FP'.
    """
    if label not in ("TP", "FP"):
        raise ValueError(f"label must be 'TP' or 'FP', got '{label}'")

    conn = get_conn()
    cur  = conn.cursor()

    # Ensure row exists
    cur.execute(
        """INSERT INTO region_thresholds (region_id, theta, tp_count, fp_count)
           VALUES (%s, %s, 0, 0)
           ON CONFLICT (region_id) DO NOTHING""",
        (region_id, THETA_DEFAULT)
    )

    # Read current state
    cur.execute(
        "SELECT theta, tp_count, fp_count FROM region_thresholds WHERE region_id = %s",
        (region_id,)
    )
    row = cur.fetchone()
    theta_before, tp, fp = row

    # Increment counter
    if label == "TP":
        tp += 1
    else:
        fp += 1

    total   = tp + fp
    precision = tp / total if total > 0 else 1.0

    # Apply recalibration rule
    theta_after = theta_before
    reason      = "no change"

    if precision < 0.30:
        theta_after = min(THETA_MAX, theta_before + DELTA_UP)
        reason      = f"precision={precision:.2f} < 0.30 → raised θ"
    elif precision > 0.70 and total < MIN_VOL:
        theta_after = max(THETA_MIN, theta_before - DELTA_DOWN)
        reason      = f"precision={precision:.2f} > 0.70, volume={total} < {MIN_VOL} → lowered θ"

    # Write back
    cur.execute(
        """UPDATE region_thresholds
           SET theta = %s, tp_count = %s, fp_count = %s, last_updated = NOW()
           WHERE region_id = %s""",
        (theta_after, tp, fp, region_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    return {
        "region_id":    region_id,
        "label":        label,
        "theta_before": round(theta_before, 4),
        "theta_after":  round(theta_after, 4),
        "tp_count":     tp,
        "fp_count":     fp,
        "precision":    round(precision, 4),
        "reason":       reason,
    }


def get_all_thresholds() -> list:
    """Return full threshold table — used by /alerts route to filter zones."""
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(
        "SELECT region_id, theta, tp_count, fp_count, last_updated FROM region_thresholds"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "region_id":    r[0],
            "theta":        r[1],
            "tp_count":     r[2],
            "fp_count":     r[3],
            "last_updated": str(r[4]),
        }
        for r in rows
    ]
