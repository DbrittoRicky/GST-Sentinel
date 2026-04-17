# src/api/models.py
from pydantic import BaseModel
from typing import Optional

class ExplainRequest(BaseModel):
    zone_id: str
    z_score: float
    date: str
    query: Optional[str] = None

class ExplainResponse(BaseModel):
    zone_id: str
    z_score: float
    explanation: str
    intent: Optional[str] = None
    context_json: Optional[dict] = None
    bullets: Optional[list] = None

class ZoneScore(BaseModel):
    zone_id: str
    z_score: float
    chl_raw: Optional[float] = None
    mu:      Optional[float] = None

class ScoresResponse(BaseModel):
    date:      str
    scores:    dict
    top_zones: list[ZoneScore]

# ── M5 additions ──────────────────────────────────────────

class AlertItem(BaseModel):
    alert_id:         int
    region_id:        str
    score:            float
    theta_used:       float
    chl_z:            Optional[float] = None
    persistence_days: int
    current_theta:    float
    risk_label:       str

class AlertsResponse(BaseModel):
    date:   str
    count:  int
    alerts: list[AlertItem]

class HistoryPoint(BaseModel):
    date:             str
    score:            float
    chl_z:            Optional[float] = None
    persistence_days: int
    theta_used:       Optional[float] = None
    risk_label:       str

class ZoneHistoryResponse(BaseModel):
    zone_id: str
    days:    int
    count:   int
    history: list[HistoryPoint]

class FeedbackRequest(BaseModel):
    label:   str
    user_id: str = "demo"
