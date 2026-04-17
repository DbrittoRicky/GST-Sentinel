import numpy as np
import torch
import pandas as pd
import os
from pathlib import Path

# ── Dynamic path resolution ───────────────────────────────────────────────────
# This file lives at: <repo_root>/src/model/score.py
# .parents[0] = src/model
# .parents[1] = src
# .parents[2] = repo root
REPO_ROOT  = Path(__file__).resolve().parents[2]
PROCESSED  = REPO_ROOT / "data" / "processed"
SCORES_DIR = PROCESSED / "scores"
CKPT_DIR   = REPO_ROOT / "checkpoints"
MODEL_FILE = CKPT_DIR / "sentinel_gnn.pt"

# ── Hyperparams (match train.py) ──────────────────────────────────────────────
WINDOW             = 14
HIDDEN_DIM         = 32
PERSISTENCE_THRESH = 2.0
DEMO_DAYS          = 90          # how many trailing days to score
DEVICE             = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ── Late import of model (same package) ──────────────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import STGNNModel


def verify_artifacts():
    """Check all required files exist before doing any work."""
    required = {
        "anomaly_tensor": PROCESSED / "anomaly_tensor.npy",
        "climatology_sigma": PROCESSED / "climatology_sigma.npy",
        "graph": PROCESSED / "graph.pt",
        "checkpoint": MODEL_FILE,
    }
    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"\n❌ Missing required files: {missing}"
            f"\n   Expected under: {REPO_ROOT}"
            f"\n   Run the pipeline stages first:\n"
            f"     python src/pipeline/download.py\n"
            f"     python src/pipeline/climatology.py\n"
            f"     python src/pipeline/zscore.py\n"
            f"     python src/graph/build_graph.py\n"
            f"     python src/model/train.py"
        )
    print(f"✅ All artifacts found under {REPO_ROOT}")


def load_times(T: int) -> np.ndarray:
    """
    Load timestamps from times.npy if it exists,
    otherwise synthesise a date range ending 2024-12-31.
    """
    times_path = PROCESSED / "times.npy"
    if times_path.exists():
        times = np.load(times_path, allow_pickle=True)
        print(f"   Loaded {len(times)} timestamps from times.npy")
    else:
        times = pd.date_range(end="2024-12-31", periods=T, freq="D").values
        print(f"   times.npy not found — synthesised {T} daily timestamps ending 2024-12-31")
    return times


def score_demo_window():
    print(f"\n{'='*55}")
    print(f"  GST-Sentinel · Score Engine")
    print(f"  Repo root : {REPO_ROOT}")
    print(f"  Device    : {DEVICE}")
    print(f"{'='*55}\n")

    # ── Verify everything exists ──────────────────────────────────────────────
    verify_artifacts()

    # ── Load artifacts ────────────────────────────────────────────────────────
    os.makedirs(SCORES_DIR, exist_ok=True)

    anomaly = np.load(PROCESSED / "anomaly_tensor.npy")       # (N, T, 1)
    sigma   = np.load(PROCESSED / "climatology_sigma.npy")    # (N, 366)
    graph   = torch.load(PROCESSED / "graph.pt", map_location="cpu", weights_only=False)

    N, T, F = anomaly.shape
    times   = load_times(T)

    print(f"\n   Tensor  : {anomaly.shape}  (nodes × time × features)")
    print(f"   Sigma   : {sigma.shape}")
    print(f"   Graph   : {graph.num_nodes} nodes, {graph.edge_index.shape[1]} edges")
    print(f"   Scoring : last {DEMO_DAYS} days of {T} total timesteps\n")

    # ── Push graph to device ──────────────────────────────────────────────────
    edge_index  = graph.edge_index.to(DEVICE)
    edge_weight = (
        graph.edge_attr[:, 0].to(DEVICE)
        if graph.edge_attr is not None else None
    )

    # ── Load model ────────────────────────────────────────────────────────────
    model = STGNNModel(in_channels=F, hidden_dim=HIDDEN_DIM, window=WINDOW).to(DEVICE)
    model.load_state_dict(torch.load(MODEL_FILE, map_location=DEVICE,weights_only=False))
    model.eval()
    print(f"   Model loaded from: {MODEL_FILE.relative_to(REPO_ROOT)}")

    # ── Score loop ────────────────────────────────────────────────────────────
    demo_start  = max(WINDOW, T - DEMO_DAYS)
    persistence = np.zeros(N, dtype=int)
    written     = 0

    with torch.no_grad():
        for t in range(demo_start, T):
            date = pd.Timestamp(times[t]).strftime("%Y-%m-%d")

            # Input window: (N, WINDOW, F)
            x    = torch.tensor(anomaly[:, t - WINDOW : t, :], dtype=torch.float32).to(DEVICE)
            pred = model(x, edge_index, edge_weight).squeeze(-1).cpu().numpy()  # (N,)

            actual   = anomaly[:, t, 0]        # (N,)
            residual = actual - pred            # (N,)

            # Season-normalise residual by day-of-year climatological std
            doy     = min(pd.Timestamp(times[t]).day_of_year, 365)
            sigma_d = np.maximum(sigma[:, doy], 0.1)
            score   = residual / sigma_d        # (N,)  ← double-baseline anomaly score

            # Increment persistence counter for cells above threshold
            persistence = np.where(score >= PERSISTENCE_THRESH, persistence + 1, 0)

            # Build output dataframe
            df = pd.DataFrame({
                "region_id":        [f"IN-R{i+1:04d}" for i in range(N)],
                "date":             date,
                "chl_z":            actual.round(4),
                "predicted_z":      pred.round(4),
                "score":            score.round(4),
                "persistence_days": persistence,
                "alert":            (persistence >= 3).astype(int),  # 3-day bloom flag
            })
            df.to_csv(SCORES_DIR / f"scores_{date}.csv", index=False)
            written += 1

    print(f"\n✅ Done — {written} daily score files → {SCORES_DIR.relative_to(REPO_ROOT)}/")
    print(f"   Alert threshold : score ≥ {PERSISTENCE_THRESH} for ≥ 3 consecutive days")

    # ── Quick summary ─────────────────────────────────────────────────────────
    last_csv = SCORES_DIR / f"scores_{pd.Timestamp(times[T-1]).strftime('%Y-%m-%d')}.csv"
    last_df  = pd.read_csv(last_csv)
    n_alerts = last_df["alert"].sum()
    print(f"\n   Last day alerts : {n_alerts} / {N} zones flagged")
    print(f"   Latest file     : {last_csv.name}")


if __name__ == "__main__":
    score_demo_window()