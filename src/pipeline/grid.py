# src/pipeline/grid.py
import numpy as np
import geopandas as gpd
from shapely.geometry import box
import json, os

LAT_MIN, LAT_MAX = 5.0, 25.0
LON_MIN, LON_MAX = 60.0, 100.0
STEP = 0.25  # ~25km per cell

def build_grid():
    os.makedirs("data/processed", exist_ok=True)
    lats = np.arange(LAT_MIN, LAT_MAX, STEP)
    lons = np.arange(LON_MIN, LON_MAX, STEP)

    features = []
    zone_id = 1
    for lat in lats:
        for lon in lons:
            centroid_lat = lat + STEP / 2
            centroid_lon = lon + STEP / 2
            geom = box(lon, lat, lon + STEP, lat + STEP)
            features.append({
                "type": "Feature",
                "geometry": geom.__geo_interface__,
                "properties": {
                    "zone_id": f"IN-R{zone_id:04d}",
                    "centroid_lat": round(centroid_lat, 4),
                    "centroid_lon": round(centroid_lon, 4),
                    "lat_idx": int(round((lat - LAT_MIN) / STEP)),
                    "lon_idx": int(round((lon - LON_MIN) / STEP)),
                }
            })
            zone_id += 1

    geojson = {"type": "FeatureCollection", "features": features}
    out_path = "data/processed/zones.geojson"
    with open(out_path, "w") as f:
        json.dump(geojson, f)

    print(f"Grid built: {len(features)} zones → {out_path}")
    return len(features)

if __name__ == "__main__":
    n = build_grid()
    # Expected output: Grid built: 6400 zones → data/processed/zones.geojson
    # (~80 lon steps × 80 lat steps = 6400 — but coastal masking in later modules will trim this)