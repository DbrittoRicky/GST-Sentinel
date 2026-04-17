# src/model/model.py
import torch
import torch.nn as nn
from torch_geometric.nn import GCNConv

class STGNNModel(nn.Module):
    """
    Lightweight CSTGL-inspired STGNN:
    - Temporal branch: 1D Conv over 14-day window
    - Spatial branch: GCNConv over correlation-weighted graph
    - Output: next-day anomaly forecast per node (scalar)
    """
    def __init__(self, in_channels=1, hidden_dim=32, window=14):
        super().__init__()
        self.window = window

        # Temporal encoder: treat window as channel dimension
        self.temporal_conv = nn.Conv1d(
            in_channels=in_channels,
            out_channels=hidden_dim,
            kernel_size=window,
            padding=0
        )  # output shape: (N, hidden_dim, 1)

        # Graph conv over spatial edges
        self.graph_conv = GCNConv(hidden_dim, hidden_dim)

        # Final regression head
        self.head = nn.Linear(hidden_dim, 1)

    def forward(self, x, edge_index, edge_weight=None):
        """
        x: (N, window, F) — last `window` days of anomaly features per node
        edge_index: (2, E)
        edge_weight: (E,) optional
        Returns: (N, 1) next-day forecast
        """
        N, W, F = x.shape
        # x → (N, F, W) for Conv1d
        h = x.permute(0, 2, 1)               # (N, F, W)
        h = self.temporal_conv(h)             # (N, hidden_dim, 1)
        h = h.squeeze(-1)                     # (N, hidden_dim)
        h = torch.relu(h)

        # Graph message passing
        h = self.graph_conv(h, edge_index, edge_weight)  # (N, hidden_dim)
        h = torch.relu(h)

        return self.head(h)   # (N, 1)