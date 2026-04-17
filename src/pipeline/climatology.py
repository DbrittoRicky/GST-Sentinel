# src/pipeline/climatology.py
import xarray as xr
import numpy as np
import json
import os
from pathlib import Path

SIGMA_MIN = 0.1  # floor to prevent division suppression in low-variance zones
PROCESSED_DIR = "data/processed"

def load_zones():
    with open(f"{PROCESSED_DIR}/zones.geojson") as f:
        gj = json.load(f)
    zones = [feat["properties"] for feat in gj["features"]]
    return zones

def assign_pixels_to_zones(ds, zones, step=0.25):
    """Map each zone to the nearest NetCDF lat/lon indices."""
    lats = ds.latitude.values
    lons = ds.longitude.values
    zone_pixel_map = {}
    for z in zones:
        clat, clon = z["centroid_lat"], z["centroid_lon"]
        lat_idx = int(np.argmin(np.abs(lats - clat)))
        lon_idx = int(np.argmin(np.abs(lons - clon)))
        zone_pixel_map[z["zone_id"]] = (lat_idx, lon_idx)
    return zone_pixel_map

def compute_climatology():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    nc_path = "data/raw/chl_historical/chl_india_2019_2023.nc"

    print("Loading NetCDF...")
    ds = xr.open_dataset(nc_path)
    chl = ds["CHL"]  # shape: (time, lat, lon)
    times = ds.time.values  # numpy datetime64 array

    zones = load_zones()
    zone_ids = [z["zone_id"] for z in zones]
    N = len(zones)
    T = len(times)

    print(f"Dataset: {T} days, {N} zones")
    zone_pixel_map = assign_pixels_to_zones(ds, zones)

    # Extract per-zone time series: shape (N, T)
    print("Extracting zone time series...")
    zone_series = np.full((N, T), np.nan)
    for i, z in enumerate(zones):
        lat_idx, lon_idx = zone_pixel_map[z["zone_id"]]
        vals = chl.values[:, lat_idx, lon_idx]
        zone_series[i] = vals

    # Compute day-of-year index for each timestep
    import pandas as pd
    doys = np.array([pd.Timestamp(t).day_of_year for t in times])  # 1-365

    # Compute μ(i, d) and σ(i, d) for each zone × day-of-year
    print("Computing climatology (μ and σ per zone × DOY)...")
    mu = np.full((N, 366), np.nan)
    sigma = np.full((N, 366), np.nan)

    for d in range(1, 366):
        mask = (doys == d)
        if mask.sum() == 0:
            continue
        vals = zone_series[:, mask]  # (N, years_with_this_doy)
        mu[:, d] = np.nanmean(vals, axis=1)
        sigma[:, d] = np.nanstd(vals, axis=1)

    # Fill DOY 366 (leap day) using DOY 365 values
    mu[:, 0] = mu[:, 1]       # index 0 unused, set to DOY 1
    mu[:, 365] = mu[:, 364]   # DOY 366 = copy of DOY 365
    sigma[:, 365] = sigma[:, 364]

    # Apply sigma floor
    sigma = np.where(sigma < SIGMA_MIN, SIGMA_MIN, sigma)
    # Replace NaN μ with 0 (open ocean with no data gaps)
    mu = np.where(np.isnan(mu), 0.0, mu)

    np.save(f"{PROCESSED_DIR}/climatology_mu.npy", mu)
    np.save(f"{PROCESSED_DIR}/climatology_sigma.npy", sigma)
    np.save(f"{PROCESSED_DIR}/zone_series.npy", zone_series)
    np.save(f"{PROCESSED_DIR}/times.npy", times)

    print(f"Saved: climatology_mu.npy {mu.shape}, climatology_sigma.npy {sigma.shape}")
    print(f"Saved: zone_series.npy {zone_series.shape}")
    ds.close()

if __name__ == "__main__":
    compute_climatology()