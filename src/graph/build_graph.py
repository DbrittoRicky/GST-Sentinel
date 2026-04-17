# src/graph/build_graph.py
import numpy as np
import json
import torch
from torch_geometric.data import Data
import os

PROCESSED_DIR = "src\pipeline\data\processed"
CORR_THRESHOLD = 0.2   # prune weak edges
DIST_WEIGHT    = 0.5   # balance spatial vs correlation in edge weight

def haversine(lat1, lon1, lat2, lon2):
    """Returns distance in km."""
    import math
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def build_graph():
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # ── Load inputs ──────────────────────────────────────────────────
    with open(f"{PROCESSED_DIR}/zones.geojson") as f:
        zones = json.load(f)["features"]
    N = len(zones)
    corr = np.load(f"{PROCESSED_DIR}/corr_matrix.npy")  # (N, N)

    centroids = np.array([
        [z["properties"]["centroid_lat"], z["properties"]["centroid_lon"]]
        for z in zones
    ], dtype=np.float32)

    # ── 8-neighbour (queen's case) spatial adjacency ──────────────────
    STEP = 0.25
    edge_src, edge_dst, edge_weights = [], [], []

    for i in range(N):
        lat_i = zones[i]["properties"]["centroid_lat"]
        lon_i = zones[i]["properties"]["centroid_lon"]
        for j in range(N):
            if i == j:
                continue
            lat_j = zones[j]["properties"]["centroid_lat"]
            lon_j = zones[j]["properties"]["centroid_lon"]
            dlat = abs(lat_i - lat_j)
            dlon = abs(lon_i - lon_j)
            # 8-neighbours: within 1 step in both lat and lon
            if dlat <= STEP * 1.01 and dlon <= STEP * 1.01:
                c = corr[i, j]
                if c < CORR_THRESHOLD:
                    continue
                d = haversine(lat_i, lon_i, lat_j, lon_j)
                w = np.exp(-d / 100.0) * DIST_WEIGHT + c * (1 - DIST_WEIGHT)
                edge_src.append(i)
                edge_dst.append(j)
                edge_weights.append(w)

    edge_index = torch.tensor([edge_src, edge_dst], dtype=torch.long)   # (2, E)
    edge_attr  = torch.tensor(edge_weights, dtype=torch.float).unsqueeze(1)  # (E, 1)
    pos        = torch.tensor(centroids, dtype=torch.float)              # (N, 2)

    graph = Data(edge_index=edge_index, edge_attr=edge_attr, pos=pos, num_nodes=N)
    torch.save(graph, f"{PROCESSED_DIR}/graph.pt")

    print(f"✅ Graph saved | Nodes: {N} | Edges: {edge_index.shape[1]} | "
          f"Avg deg: {edge_index.shape[1]/N:.1f}")

if __name__ == "__main__":
    build_graph()