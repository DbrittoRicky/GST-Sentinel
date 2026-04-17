# src/api/scorer.py
import pandas as pd
import os
from pathlib import Path

# Resolve paths relative to repo root (works regardless of where you run from)
REPO_ROOT  = Path(__file__).resolve().parents[2]
SCORES_DIR = REPO_ROOT / "data" / "processed" / "scores"

_cache = {}   # { date_str: DataFrame } — in-memory cache per date

def _load_csv(date_str: str):
    """Load the GNN score CSV for a given date. Returns DataFrame or None."""
    if date_str in _cache:
        return _cache[date_str]

    # GNN score.py writes: scores2023-12-31.csv  (no hyphen after 'scores')
    path = SCORES_DIR / f"scores{date_str}.csv"
    if not path.exists():
        # Fallback: try with hyphen separator
        path = SCORES_DIR / f"scores-{date_str}.csv"
    if not path.exists():
        return None

    df = pd.read_csv(path)
    _cache[date_str] = df
    return df

def get_available_dates() -> list:
    """Return sorted list of all scored dates (YYYY-MM-DD)."""
    if not SCORES_DIR.exists():
        print(f"WARNING: scores dir not found at {SCORES_DIR}")
        return []
    dates = []
    for f in sorted(SCORES_DIR.glob("scores*.csv")):
        # Strip 'scores' or 'scores-' prefix → '2023-10-03'
        stem = f.stem  # e.g. 'scores2023-10-03'
        date_part = stem.replace("scores-", "").replace("scores", "")
        if len(date_part) == 10:   # YYYY-MM-DD
            dates.append(date_part)
    return sorted(dates)

def get_scores_for_date(date_str: str) -> dict:
    """Returns { zone_id: z_score } for a given date string YYYY-MM-DD."""
    df = _load_csv(date_str)

    if df is None:
        # MOCK fallback — deterministic so map colours are stable per date
        import random, hashlib
        seed = int(hashlib.md5(date_str.encode()).hexdigest()[:8], 16)
        rng  = random.Random(seed)
        mock_zones = [f"IN-R{i:04d}" for i in range(1, 201)]
        print(f"MOCK mode for {date_str} — CSV not found in {SCORES_DIR}")
        return {z: round(rng.gauss(0, 1.2), 3) for z in mock_zones}

    # CSV columns from score.py: region_id, score, chl_z, persistence_days, alert
    id_col    = "region_id" if "region_id" in df.columns else df.columns[0]
    score_col = "score"     if "score"     in df.columns else "chl_z"

    return {
        str(row[id_col]): round(float(row[score_col]), 4)
        for _, row in df.iterrows()
    }

def get_top_zones(scores: dict, n: int = 10) -> list:
    """Return top-N zones by score descending."""
    sorted_zones = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{"zone_id": zid, "z_score": round(zscore, 4)}
            for zid, zscore in sorted_zones[:n]]