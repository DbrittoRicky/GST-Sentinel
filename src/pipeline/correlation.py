# src/pipeline/correlation.py
import numpy as np
import os

PROCESSED_DIR = "data/processed"

def compute_correlation():
    print("Loading anomaly tensor...")
    anomaly_tensor = np.load(f"{PROCESSED_DIR}/anomaly_tensor.npy")  # (N, T, 1)
    series = anomaly_tensor[:, :, 0]  # (N, T)

    N, T = series.shape
    print(f"Computing {N}×{N} correlation matrix ({N*N:,} pairs)...")

    # Use numpy corrcoef — works for moderate N (~6400)
    # For very large N, use chunked computation
    corr_matrix = np.corrcoef(series)  # (N, N)

    # Replace NaN (constant zones — all-zero series) with 0
    corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)

    np.save(f"{PROCESSED_DIR}/corr_matrix.npy", corr_matrix)

    print(f"Correlation matrix shape: {corr_matrix.shape}")
    print(f"Value range: [{corr_matrix.min():.3f}, {corr_matrix.max():.3f}]")
    print(f"Mean off-diagonal: {corr_matrix[corr_matrix != 1.0].mean():.4f}")
    print(f"Saved: corr_matrix.npy")

if __name__ == "__main__":
    compute_correlation()