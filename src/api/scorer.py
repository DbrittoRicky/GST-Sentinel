# src/api/scorer.py
import numpy as np
import json
import pandas as pd
import os
from pathlib import Path

PROCESSED_DIR = Path("data/processed")
_tensor = None          # (N, T, 1)
_zones  = None          # list of zone property dicts
_times  = None          # list of date strings YYYY-MM-DD
_loaded = False

def _try_load():
    global _tensor, _zones, _times, _loaded
    tensor_path = PROCESSED_DIR / "anomaly_tensor.npy"
    zones_path  = PROCESSED_DIR / "zones.geojson"
    times_path  = PROCESSED_DIR / "times.npy"

    if not (tensor_path.exists() and zones_path.exists() and times_path.exists()):
        print("WARNING: Tensor/zones not found — running in MOCK mode.")
        return False

    _tensor = np.load(tensor_path)                              # (N, T, 1)
    raw_times = np.load(times_path, allow_pickle=True)
    _times = [pd.Timestamp(t).strftime("%Y-%m-%d") for t in raw_times]

    with open(zones_path) as f:
        gj = json.load(f)
    _zones = [feat["properties"] for feat in gj["features"]]
    _loaded = True
    print(f"Scorer loaded: {len(_zones)} zones × {len(_times)} days.")
    return True

def get_scores_for_date(date_str: str) -> dict:
    """Returns { zone_id: z_score } for a given date string YYYY-MM-DD."""
    if not _loaded:
        _try_load()

    if not _loaded:
        # Mock mode: generate plausible random scores for demo
        import random, hashlib
        seed = int(hashlib.md5(date_str.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        mock_zones = [f"IN-R{i:03d}" for i in range(1, 201)]
        return {z: round(rng.gauss(0, 1.2), 3) for z in mock_zones}

    if date_str not in _times:
        return {}

    t_idx = _times.index(date_str)
    scores = {}
    for i, z in enumerate(_zones):
        val = float(_tensor[i, t_idx, 0])
        scores[z["zone_id"]] = round(val, 4)
    return scores

def get_top_zones(scores: dict, n: int = 10) -> list:
    """Return top-N zones by z_score descending."""
    sorted_zones = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{"zone_id": zid, "z_score": zscore} for zid, zscore in sorted_zones[:n]]

# Pre-load on import
_try_load()