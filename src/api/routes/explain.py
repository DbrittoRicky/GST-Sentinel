# src/api/routes/explain.py
#
# Module 7 — RAG NL Explain Interface
# ─────────────────────────────────────────────────────────────────────────────
# Stage 1  Intent Resolver     → classify query into one of 3 intents
# Stage 2  Context Packager    → pull closed-world JSON from NeonDB only
# Stage 3  Grounded Prompt     → LLM call + output validator
# ─────────────────────────────────────────────────────────────────────────────

import os
import re
import json
import httpx
import math
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from src.api.database import get_conn, release_conn

load_dotenv()

OLLAMA_HOST    = os.getenv("OLLAMA_HOST",    "http://localhost:11434")
OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL",   "qwen3:8b")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY",   "")
GROQ_MODEL     = os.getenv("GROQ_MODEL",     "llama3-8b-8192")
TOP_K_ALERTS   = int(os.getenv("RAG_TOP_K",       "5"))
HISTORY_DAYS   = int(os.getenv("RAG_HISTORY",      "30"))
NEIGHBOR_LIMIT = int(os.getenv("RAG_NEIGHBORS",    "3"))

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    zone_id: str
    z_score: float
    date:    str
    query:   Optional[str] = None     # freeform NL query; if omitted → zone_specific


class ExplainResponse(BaseModel):
    zone_id:      str
    z_score:      float
    explanation:  str
    intent:       Optional[str]  = None
    context_json: Optional[dict] = None
    bullets:      Optional[list] = None


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Intent Resolver
# ─────────────────────────────────────────────────────────────────────────────

_ATTENTION_KEYWORDS = {
    "attention", "now", "critical", "today", "urgent", "top", "worst",
    "highest", "risk", "current", "alert", "priority",
}
_TREND_KEYWORDS = {
    "trend", "week", "month", "history", "over time", "last", "days",
    "change", "evolving", "pattern", "compare", "30",
}
_ZONE_KEYWORDS = {
    "why", "what", "explain", "cause", "reason", "anomaly", "zone",
    "high", "elevated", "happening", "this zone",
}


def _resolve_intent(query: Optional[str], zone_id: str) -> str:
    if not query:
        return "zone_specific"
    q = query.lower()
    scores = {
        "attention_now": sum(1 for w in _ATTENTION_KEYWORDS if w in q),
        "trend":         sum(1 for w in _TREND_KEYWORDS     if w in q),
        "zone_specific": sum(1 for w in _ZONE_KEYWORDS      if w in q),
    }
    resolved = max(scores, key=scores.get)
    return resolved if scores[resolved] > 0 else "zone_specific"


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Context Packager
# ─────────────────────────────────────────────────────────────────────────────

def _safe(val, digits=4):
    if val is None:
        return None
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, digits)
    except (TypeError, ValueError):
        return None


def _build_context(intent: str, zone_id: str, date: str, top_k: int = TOP_K_ALERTS) -> dict:
    conn = get_conn()
    try:
        cur = conn.cursor()
        context: dict = {"query_date": date, "intent": intent, "zones": []}

        if intent == "attention_now":
            cur.execute("""
                SELECT a.region_id, a.score, a.chl_z, a.persistence_days,
                       rt.theta, rt.tp_count, rt.fp_count
                FROM   alerts a
                LEFT JOIN region_thresholds rt ON rt.region_id = a.region_id
                WHERE  a.alert_date = %s
                ORDER  BY a.score DESC
                LIMIT  %s
            """, (date, top_k))
            for r in cur.fetchall():
                region_id, score, chl_z, pers, theta, tp, fp = r
                context["zones"].append({
                    "region_id":        region_id,
                    "score":            _safe(score),
                    "chl_z":            _safe(chl_z),
                    "persistence_days": pers,
                    "theta":            _safe(theta) or 2.0,
                    "tp_count":         tp or 0,
                    "fp_count":         fp or 0,
                })

        elif intent == "zone_specific":
            cur.execute("""
                SELECT a.score, a.chl_z, a.sst_z, a.persistence_days,
                       rt.theta, rt.tp_count, rt.fp_count
                FROM   alerts a
                LEFT JOIN region_thresholds rt ON rt.region_id = a.region_id
                WHERE  a.region_id = %s AND a.alert_date = %s
                LIMIT  1
            """, (zone_id, date))
            row = cur.fetchone()

            zone_entry: dict = {
                "region_id": zone_id, "score": None, "chl_z": None,
                "sst_z": None, "persistence_days": 1, "theta": 2.0,
                "tp_count": 0, "fp_count": 0, "history_30d": [], "neighbors": [],
            }
            if row:
                score, chl_z, sst_z, pers, theta, tp, fp = row
                zone_entry.update({
                    "score":            _safe(score),
                    "chl_z":            _safe(chl_z),
                    "sst_z":            _safe(sst_z),
                    "persistence_days": pers,
                    "theta":            _safe(theta) or 2.0,
                    "tp_count":         tp or 0,
                    "fp_count":         fp or 0,
                })

            # 30-day history from alerts table
            cur.execute("""
                SELECT alert_date, score, chl_z
                FROM   alerts
                WHERE  region_id = %s
                  AND  alert_date BETWEEN (%s::date - INTERVAL '30 days') AND %s::date
                ORDER  BY alert_date ASC
            """, (zone_id, date, date))
            zone_entry["history_30d"] = [
                {"date": str(r[0]), "score": _safe(r[1]), "chl_z": _safe(r[2])}
                for r in cur.fetchall()
            ]

            # Neighboring zones
            cur.execute("""
                SELECT region_id, score, chl_z, persistence_days
                FROM   alerts
                WHERE  alert_date = %s AND region_id != %s
                ORDER  BY score DESC
                LIMIT  %s
            """, (date, zone_id, NEIGHBOR_LIMIT))
            zone_entry["neighbors"] = [
                {"region_id": r[0], "score": _safe(r[1]),
                 "chl_z": _safe(r[2]), "persistence_days": r[3]}
                for r in cur.fetchall()
            ]
            context["zones"].append(zone_entry)

        elif intent == "trend":
            cur.execute("""
                SELECT alert_date, score, chl_z
                FROM   alerts
                WHERE  region_id = %s
                  AND  alert_date BETWEEN (%s::date - INTERVAL '30 days') AND %s::date
                ORDER  BY alert_date ASC
            """, (zone_id, date, date))
            history = cur.fetchall()
            scores_list = [float(r[1]) for r in history if r[1] and math.isfinite(float(r[1]))]

            cur.execute("SELECT theta FROM region_thresholds WHERE region_id = %s", (zone_id,))
            theta_row = cur.fetchone()
            theta_val = float(theta_row[0]) if theta_row else 2.0

            context["zones"].append({
                "region_id":   zone_id,
                "theta":       round(theta_val, 4),
                "history_30d": [
                    {"date": str(r[0]), "score": _safe(r[1]), "chl_z": _safe(r[2])}
                    for r in history
                ],
                "summary": {
                    "max_score":        round(max(scores_list), 4)  if scores_list else None,
                    "min_score":        round(min(scores_list), 4)  if scores_list else None,
                    "mean_score":       round(sum(scores_list) / len(scores_list), 4) if scores_list else None,
                    "days_above_theta": sum(1 for s in scores_list if s >= theta_val),
                },
            })

        cur.close()
        return context
    finally:
        release_conn(conn)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3a — Prompt Builder
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are a marine scientist assistant analyzing Indian Ocean / Arabian Sea chlorophyll-a anomalies. "
    "Answer ONLY using the data provided in the context JSON below. "
    "Do NOT invent zone IDs, scores, or events not present in the context. "
    "Output EXACTLY 3 bullet points (start each with '- '). "
    "Each bullet must cite a specific zone_id and numerical value from the context. "
    "Be concise — max 30 words per bullet."
)

_INTENT_INSTRUCTIONS = {
    "attention_now": (
        "The user wants to know which zones need immediate attention today. "
        "Rank the top 3 zones by risk. For each, state region_id, score, persistence, and why it's critical."
    ),
    "zone_specific": (
        "The user wants to understand why this specific zone is showing a high anomaly. "
        "Explain the score magnitude, chl_z component, persistence streak, and how it compares to neighbors."
    ),
    "trend": (
        "The user wants a 30-day trend analysis for this zone. "
        "Describe the trend direction (rising/falling/stable), peak date and value, "
        "and how many days the zone exceeded its adaptive threshold (theta)."
    ),
}


def _build_prompt(intent: str, context: dict) -> str:
    instruction = _INTENT_INSTRUCTIONS.get(intent, _INTENT_INSTRUCTIONS["zone_specific"])
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"INTENT: {intent}\n"
        f"INSTRUCTION: {instruction}\n\n"
        f"CONTEXT (ground truth — do not go beyond this):\n{json.dumps(context, indent=2)}\n\n"
        f"RESPONSE (3 bullets, citing zone IDs and numbers from the context only):"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3b — Output Validator
# ─────────────────────────────────────────────────────────────────────────────

def _extract_valid_zone_ids(context: dict) -> set:
    valid = set()
    for z in context.get("zones", []):
        if z.get("region_id"):
            valid.add(z["region_id"])
        for n in z.get("neighbors", []):
            if n.get("region_id"):
                valid.add(n["region_id"])
    return valid


def _validate_output(llm_text: str, valid_ids: set) -> tuple[str, list[str]]:
    zone_id_pattern = re.compile(r"\bIN-R\d{3,6}\b", re.IGNORECASE)
    raw_lines   = [l.strip() for l in llm_text.split("\n") if l.strip()]
    bullets_raw = [l for l in raw_lines if l.startswith("-")] or raw_lines[:3]

    clean_bullets = []
    for line in bullets_raw:
        for fid in zone_id_pattern.findall(line):
            if fid.upper() not in {v.upper() for v in valid_ids}:
                line = line.replace(fid, "[zone]")
        clean_bullets.append(line)

    return "\n".join(clean_bullets), clean_bullets


# ─────────────────────────────────────────────────────────────────────────────
# LLM Callers
# ─────────────────────────────────────────────────────────────────────────────

async def _call_ollama(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=45) as client:
        res = await client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        )
        res.raise_for_status()
        return res.json()["response"].strip()


async def _call_groq(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=25) as client:
        res = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model":       GROQ_MODEL,
                "messages":    [{"role": "user", "content": prompt}],
                "max_tokens":  300,
                "temperature": 0.2,
            },
        )
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()


def _static_fallback(intent: str, context: dict, zone_id: str, z_score: float, date: str) -> str:
    if intent == "attention_now" and context["zones"]:
        z = context["zones"][0]
        return (
            f"- {z['region_id']} is the top alert on {date} with score {z['score']}σ "
            f"(persisted {z.get('persistence_days', 1)} days).\n"
            f"- Adaptive threshold (θ={z.get('theta', 2.0)}) was exceeded; "
            f"TP={z.get('tp_count', 0)}, FP={z.get('fp_count', 0)}.\n"
            f"- AI explanation unavailable — verify via /api/zones/{z['region_id']}/history."
        )
    return (
        f"- Zone {zone_id} shows a {z_score:.2f}σ anomaly on {date}.\n"
        f"- This may reflect upwelling or monsoon-driven nutrient flux in the Indian EEZ.\n"
        f"- AI explanation temporarily unavailable; raw context returned in context_json."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Route
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/explain", response_model=ExplainResponse)
async def explain_anomaly(req: ExplainRequest):
    # Stage 1 — Intent
    intent = _resolve_intent(req.query, req.zone_id)

    # Stage 2 — Context
    context = _build_context(intent, req.zone_id, req.date)

    # Stage 3 — LLM + Validate
    prompt    = _build_prompt(intent, context)
    valid_ids = _extract_valid_zone_ids(context)

    raw_llm = ""
    try:
        raw_llm = await _call_ollama(prompt)
    except Exception as e:
        print(f"[explain] Ollama unavailable ({e}), trying Groq...")
        try:
            raw_llm = await _call_groq(prompt)
        except Exception as e2:
            print(f"[explain] Groq failed ({e2}), using static fallback.")
            raw_llm = _static_fallback(intent, context, req.zone_id, req.z_score, req.date)

    explanation, bullets = _validate_output(raw_llm, valid_ids)

    return ExplainResponse(
        zone_id=req.zone_id,
        z_score=req.z_score,
        explanation=explanation,
        intent=intent,
        context_json=context,
        bullets=bullets,
    )
