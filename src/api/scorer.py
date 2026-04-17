# src/api/scorer.py
import pandas as pd
import os
import math
from pathlib import Path

REPO_ROOT  = Path(__file__).resolve().parents[2]
SCORES_DIR = REPO_ROOT / "data" / "processed" / "scores"

_df_cache:    dict = {}   # { date_str: DataFrame }
_score_cache: dict = {}   # { date_str: { zone_id: z_score } } — fully parsed, ready to serve


def _load_csv(date_str: str):
    if date_str in _df_cache:
        return _df_cache[date_str]
    for fmt in [f"scores_{date_str}.csv", f"scores{date_str}.csv", f"scores-{date_str}.csv"]:
        path = SCORES_DIR / fmt
        if path.exists():
            df = pd.read_csv(path)
            _df_cache[date_str] = df
            return df
    return None


def get_available_dates() -> list:
    if not SCORES_DIR.exists():
        return []
    dates = []
    for f in sorted(SCORES_DIR.glob("scores*.csv")):
        stem = f.stem
        for prefix in ["scores_", "scores-", "scores"]:
            if stem.startswith(prefix):
                date_part = stem[len(prefix):]
                break
        if len(date_part) == 10:
            dates.append(date_part)
    return sorted(dates)


def get_scores_for_date(date_str: str) -> dict:
    """
    Returns { zone_id: z_score } for a given date string YYYY-MM-DD.
    First call reads + parses CSV and caches the result in memory.
    Subsequent calls for the same date return instantly from _score_cache.
    """
    # ── Memory cache hit — fastest path, zero disk/DB I/O ──
    if date_str in _score_cache:
        return _score_cache[date_str]

    df = _load_csv(date_str)

    if df is None:
        import random, hashlib
        seed = int(hashlib.md5(date_str.encode()).hexdigest()[:8], 16)
        rng  = random.Random(seed)
        mock_zones = [f"IN-R{i:04d}" for i in range(1, 201)]
        print(f"MOCK mode for {date_str} — CSV not found in {SCORES_DIR}")
        scores = {z: round(rng.gauss(0, 1.2), 3) for z in mock_zones}
        _score_cache[date_str] = scores
        return scores

    id_col    = "region_id" if "region_id" in df.columns else df.columns[0]
    score_col = "score"     if "score"     in df.columns else "chl_z"

    scores = {}
    for _, row in df.iterrows():
        zid = str(row[id_col])
        try:
            zscore = float(row[score_col])
        except (TypeError, ValueError):
            zscore = 0.0
        if not math.isfinite(zscore):
            zscore = 0.0
        scores[zid] = round(zscore, 4)

    # ── Cache the parsed result — all future requests for this date are instant ──
    _score_cache[date_str] = scores
    return scores


def get_top_zones(scores: dict, n: int = 10) -> list:
    """Return top-N zones by score descending."""
    finite_scores = []
    for zid, zscore in scores.items():
        try:
            z = float(zscore)
        except (TypeError, ValueError):
            continue
        if math.isfinite(z):
            finite_scores.append((zid, z))

    sorted_zones = sorted(finite_scores, key=lambda x: x[1], reverse=True)
    return [{"zone_id": zid, "z_score": round(zscore, 4)}
            for zid, zscore in sorted_zones[:n]]
