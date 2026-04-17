# src/api/routes/zones.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import json

router = APIRouter()
ZONES_PATH = Path("data/processed/zones.geojson")

# Cache in memory after first load
_zones_cache = None

@router.get("/zones")
async def get_zones():
    global _zones_cache
    if _zones_cache is not None:
        return JSONResponse(content=_zones_cache)

    if not ZONES_PATH.exists():
        # Return a minimal mock GeoJSON so frontend doesn't break
        mock = {
            "type": "FeatureCollection",
            "features": []
        }
        return JSONResponse(content=mock)

    with open(ZONES_PATH) as f:
        _zones_cache = json.load(f)

    return JSONResponse(content=_zones_cache)