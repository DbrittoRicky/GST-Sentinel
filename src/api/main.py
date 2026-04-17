# src/api/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.api.database import init_db
from src.api.routes import zones, scores, explain
import uvicorn

app = FastAPI(
    title="GST-Sentinel API",
    description="Indian EEZ Chlorophyll Anomaly Detection API",
    version="1.0.0"
)

# ── Startup ──
@app.on_event("startup")
async def startup():
    init_db()
    print("GST-Sentinel API started.")

# ── API Routes ──
app.include_router(zones.router,   prefix="/api")
app.include_router(scores.router,  prefix="/api")
app.include_router(explain.router, prefix="/api")

# ── Serve Dashboard UI ──
app.mount("/static", StaticFiles(directory="src/api/static"), name="static")

@app.get("/")
async def root():
    return FileResponse("src/api/static/index.html")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "gst-sentinel"}

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)