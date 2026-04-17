# src/api/main.py
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.api.database import init_db
from src.api.routes import zones, scores, explain, feedback, alerts   # ← added alerts
import uvicorn

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(
    title="GST-Sentinel API",
    description="Indian EEZ Chlorophyll Anomaly Detection API",
    version="1.0.0"
)

@app.on_event("startup")
async def startup():
    init_db()
    print("GST-Sentinel API started.")

# ── API Routes ──────────────────────────────────────────────
app.include_router(zones.router,    prefix="/api")
app.include_router(scores.router,   prefix="/api")
app.include_router(explain.router,  prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(alerts.router,   prefix="/api")    # ← added

@app.get("/health")
async def health():
    return {"status": "ok", "service": "gst-sentinel"}

@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

app.mount("/css", StaticFiles(directory=os.path.join(STATIC_DIR, "css")), name="css")
app.mount("/js",  StaticFiles(directory=os.path.join(STATIC_DIR, "js")),  name="js")

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
