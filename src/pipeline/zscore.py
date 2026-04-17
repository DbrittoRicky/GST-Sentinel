# src/pipeline/zscore.py
import numpy as np
import pandas as pd
import os

PROCESSED_DIR = "data/processed"

def compute_zscore_tensor():
    print("Loading zone series and climatology...")
    zone_series = np.load(f"{PROCESSED_DIR}/zone_series.npy")    # (N, T)
    mu = np.load(f"{PROCESSED_DIR}/climatology_mu.npy")           # (N, 366)
    sigma = np.load(f"{PROCESSED_DIR}/climatology_sigma.npy")     # (N, 366)
    times = np.load(f"{PROCESSED_DIR}/times.npy", allow_pickle=True)

    N, T = zone_series.shape
    doys = np.array([pd.Timestamp(t).day_of_year for t in times])  # 1–366

    # ✅ FIX: clip DOY 366 → 365 (mu array is size 366, indices 0–365)
    doys = np.clip(doys, 1, 365)

    print(f"Computing z-scores for {N} zones × {T} days...")
    anomaly = np.full((N, T), np.nan)

    for t in range(T):
        d = doys[t]
        mu_d = mu[:, d]        # (N,)
        sigma_d = sigma[:, d]  # (N,)
        anomaly[:, t] = (zone_series[:, t] - mu_d) / sigma_d

    # Replace NaN (land/cloud gaps) with 0.0 — neutral anomaly
    anomaly = np.nan_to_num(anomaly, nan=0.0)

    # Shape: (N, T, 1) — single feature (Chl-z)
    anomaly_tensor = anomaly[:, :, np.newaxis]
    np.save(f"{PROCESSED_DIR}/anomaly_tensor.npy", anomaly_tensor)

    # Sanity check
    finite_vals = anomaly[anomaly != 0.0]
    print(f"Anomaly tensor shape: {anomaly_tensor.shape}")
    print(f"Value range: [{finite_vals.min():.2f}, {finite_vals.max():.2f}]")
    print(f"Mean: {finite_vals.mean():.4f} | Std: {finite_vals.std():.4f}")
    print("Saved: anomaly_tensor.npy")

if __name__ == "__main__":
    compute_zscore_tensor()