# src/api/models.py
from pydantic import BaseModel
from typing import Optional

class ExplainRequest(BaseModel):
    zone_id: str
    z_score: float
    date: str                        # YYYY-MM-DD

class ExplainResponse(BaseModel):
    zone_id: str
    z_score: float
    explanation: str

class ZoneScore(BaseModel):
    zone_id: str
    z_score: float
    chl_raw: Optional[float] = None
    mu: Optional[float] = None

class ScoresResponse(BaseModel):
    date: str
    scores: dict
    top_zones: list[ZoneScore]