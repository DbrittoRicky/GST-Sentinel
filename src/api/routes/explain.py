# src/api/routes/explain.py
from fastapi import APIRouter
from src.api.models import ExplainRequest, ExplainResponse
import os, httpx
from dotenv import load_dotenv

load_dotenv()
OLLAMA_HOST  = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

router = APIRouter()

def _risk_label(z: float) -> str:
    if z >= 2.5:  return "CRITICAL bloom risk"
    if z >= 1.5:  return "HIGH anomaly"
    if z >= 0.8:  return "MODERATE elevation"
    if z <= -1.5: return "significant deficit"
    return "near-normal conditions"

async def _call_ollama(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
        )
        return res.json()["response"].strip()

async def _call_groq(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
            }
        )
        return res.json()["choices"][0]["message"]["content"].strip()

@router.post("/explain", response_model=ExplainResponse)
async def explain_anomaly(req: ExplainRequest):
    risk = _risk_label(req.z_score)

    prompt = (
        f"You are a marine scientist assistant. "
        f"Zone {req.zone_id} on {req.date} shows a chlorophyll-a anomaly of {req.z_score:.2f}σ ({risk}). "
        f"In 3 sentences, explain what this means for coastal fisheries and what likely ocean conditions caused it. "
        f"Be specific to the Indian Ocean / Arabian Sea context."
    )

    explanation = ""
    # Try Ollama first (LAN GPU)
    try:
        explanation = await _call_ollama(prompt)
    except Exception as e:
        print(f"Ollama unavailable ({e}), trying Groq...")
        try:
            explanation = await _call_groq(prompt)
        except Exception as e2:
            explanation = (
                f"Zone {req.zone_id} shows a {req.z_score:.2f}σ anomaly on {req.date}, "
                f"indicating {risk}. "
                f"This may reflect upwelling patterns or monsoon-driven nutrient flux. "
                f"(AI explanation service temporarily unavailable.)"
            )

    return ExplainResponse(
        zone_id=req.zone_id,
        z_score=req.z_score,
        explanation=explanation
    )