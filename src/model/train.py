# src/model/train.py
import numpy as np
import torch
import torch.nn as nn
from torch_geometric.data import Data
import os, json
from model import STGNNModel

WINDOW      = 14
HIDDEN_DIM  = 32
EPOCHS      = 30
LR          = 1e-3
DEVICE      = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CKPT_DIR    = "checkpoints"
PROCESSED   = r"src/pipeline/data/processed"

def make_windows(tensor, window):
    """tensor: (N, T, F) → X (num_windows, N, window, F), Y (num_windows, N)"""
    N, T, F = tensor.shape
    Xs, Ys = [], []
    for t in range(window, T):
        Xs.append(tensor[:, t-window:t, :])   # (N, window, F)
        Ys.append(tensor[:, t, 0])             # (N,)   — Chl-z target
    return torch.tensor(np.array(Xs), dtype=torch.float32), \
           torch.tensor(np.array(Ys), dtype=torch.float32)

def train():
    os.makedirs(CKPT_DIR, exist_ok=True)

    # ── Load artifacts ────────────────────────────────────────────────
    anomaly = np.load(f"{PROCESSED}/anomaly_tensor.npy")   # (N, T, 1)
    graph   = torch.load(f"{PROCESSED}/graph.pt")
    N, T, F = anomaly.shape
    print(f"Tensor: {anomaly.shape} | Graph nodes: {graph.num_nodes} | Device: {DEVICE}")

    # ── Time split: first ~75% train, last ~25% val ───────────────────
    split = int(T * 0.75)
    X_tr, Y_tr = make_windows(anomaly[:, :split, :], WINDOW)
    X_va, Y_va = make_windows(anomaly[:, split:, :], WINDOW)
    print(f"Train windows: {len(X_tr)} | Val windows: {len(X_va)}")

    edge_index = graph.edge_index.to(DEVICE)
    edge_weight = graph.edge_attr[:, 0].to(DEVICE) if graph.edge_attr is not None else None

    model = STGNNModel(in_channels=F, hidden_dim=HIDDEN_DIM, window=WINDOW).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.MSELoss()

    best_val = float("inf")
    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0
        for i in range(len(X_tr)):
            x = X_tr[i].to(DEVICE)    # (N, window, F)
            y = Y_tr[i].to(DEVICE)    # (N,)
            pred = model(x, edge_index, edge_weight).squeeze(-1)
            loss = criterion(pred, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        if epoch % 5 == 0:
            model.eval()
            with torch.no_grad():
                val_loss = sum(
                    criterion(
                        model(X_va[i].to(DEVICE), edge_index, edge_weight).squeeze(-1),
                        Y_va[i].to(DEVICE)
                    ).item()
                    for i in range(len(X_va))
                ) / len(X_va)
            print(f"Epoch {epoch:3d} | Train: {total_loss/len(X_tr):.4f} | Val: {val_loss:.4f}")
            if val_loss < best_val:
                best_val = val_loss
                torch.save(model.state_dict(), f"{CKPT_DIR}/sentinel_gnn.pt")
                print(f"  → Saved checkpoint (val {best_val:.4f})")

    print(f"\n✅ Training done. Best val MSE: {best_val:.4f}")
    print(f"   Checkpoint: {CKPT_DIR}/sentinel_gnn.pt")

if __name__ == "__main__":
    train()