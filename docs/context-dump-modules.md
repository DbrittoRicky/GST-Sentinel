# GST-Sentinel – Module Context Dump

This document summarizes all core modules of GST-Sentinel, their responsibilities, tech stack, data flow, and current implementation status.

---

## High-Level Architecture

GST-Sentinel is a coastal algal bloom early-warning system for the Indian EEZ built as a modular pipeline:

- **Module 1: Data Pipeline & Climatology** — CMEMS download, AOI grid, climatology and anomaly tensor preparation.[file:2]
- **Module 2: Graph Construction** — Zone graph \(G=(V,E)\) with spatial and correlation-based edges.[file:2]
- **Module 3: ST-GNN Anomaly Engine** — CST-GL-style spatio-temporal GNN, double-baseline anomaly scoring.[file:2]
- **Module 4: Adaptive Threshold & Feedback** — Per-zone adaptive thresholds in PostgreSQL + operator feedback loop.[file:2]
- **Module 5: FastAPI Backend** — REST API surface for scores, alerts, thresholds, history, explain, zones.[file:2]
- **Module 6: Geospatial Dashboard UI** — Leaflet-based map, timeline, side panel, history sparkline, alerts list.[file:2][cite:7][cite:8]
- **Module 7: NL Explain Interface** — Intent-resolved, closed-world anomaly explanations via Ollama/Groq.[file:2]
- **Module 8: UI Polish** — Layout robustness, CSS fixes, visual coherence and responsiveness (ongoing).[file:1]

Core repo layout:

- Pipeline code: `src/pipeline/*.py`.[cite:9]
- Graph builder: `src/graph/build_graph.py`.[cite:10]
- Model code: `src/model/*.py`.[cite:11]
- API/backend: `src/api/**/*.py`.[cite:5][cite:6]
- Frontend/dashboard: `src/api/static/**/*`.[cite:7][cite:8]
- Utility scripts: `scripts/*.py`, `scripts/*.ps1`.[cite:12]

---

## Module 1 — Data Pipeline & Climatology

**Goal**  
Ingest CMEMS GlobColour data for the Indian EEZ, compute multi-year seasonal climatology, and produce anomaly tensors and correlation matrices for downstream modules.[file:2]

**Responsibilities**

- Authenticate and download CMEMS GlobColour Chl-a (and optional SST) products.
- Define a coarse grid over the Indian EEZ and map 4 km pixels to grid cells (\(~400\) zones).
- Compute \( \mu(i,d) \) and \( \sigma(i,d) \) per zone and day-of-year.
- Convert daily observations to climatological anomalies (z-scores).
- Compute zone-to-zone correlation matrix for graph edge weights.[file:2]

**Implementation**

- **CMEMS download** — `src/pipeline/download.py` handles CMEMS product download and local storage of NetCDFs for historical and NRT windows.[cite:9]
- **Grid & AOI** — `src/pipeline/grid.py` defines the AOI bounding box and coarse grid, producing a zone index per pixel.[cite:9]
- **Climatology** — `src/pipeline/climatology.py` computes long-run mean and std per zone/day-of-year.[cite:9]
- **Z-score & feature tensor** — `src/pipeline/zscore.py` converts daily fields to anomaly features and builds the tensor \(X[N,T,F]\).[cite:9]
- **Correlation matrix** — `src/pipeline/correlation.py` computes Pearson correlation between zone time series and writes `corr_matrix.npy`.[cite:9]

**Artifacts**

- `data/raw/*` — CMEMS NetCDFs (local-only, gitignored).
- `data/processed/climatology_*` — climatological tables/arrays.
- `data/processed/zscore_*` — anomaly tensors.
- `data/processed/corr_matrix.npy` — correlation matrix for Module 2.[file:2]

**Status:** Code complete; execution relies on local CMEMS credentials/data (not committed by design).[cite:9][file:2]

---

## Module 2 — Graph Construction

**Goal**  
Turn AOI zones and anomaly/correlation artifacts into a graph usable by PyTorch Geometric.[file:2]

**Responsibilities**

- Represent each AOI grid cell as a node with ID and centroid.
- Build edges from spatial adjacency and refine with inter-zone correlation.
- Compute edge weights combining distance and correlation.
- Serialize the graph for use by the GNN.[file:2]

**Implementation**

- `src/graph/build_graph.py` reads `zones.geojson`, `corr_matrix.npy`, and anomaly features, then constructs:
  - `edge_index` \([2, |E|]\)
  - `edge_attr` (edge weights)
  - node feature mappings.[cite:10][file:2]
- Produces `graph.pt` (PyTorch Geometric graph object) consumed by Module 3.[cite:10]

**Artifacts**

- `zones.geojson` — zone geometries and IDs (local artifact).
- `graph.pt` — serialized PyG graph.[file:2]

**Status:** Graph builder implemented; `graph.pt` generated locally during pipeline runs.[cite:10][file:1]

---

## Module 3 — ST-GNN Anomaly Engine

**Goal**  
Train and run a CST-GL-style spatio-temporal GNN on the constructed graph to produce next-day anomaly forecasts and double-baseline residual scores.[file:2]

**Responsibilities**

- Define CST-GL-like architecture adapted to irregular grid graph.
- Train model on 2019–2022, validate on 2023, generate scores for 2023‑10–2023‑12.
- Compute double-baseline anomaly score
  \[
  s_{i,t} = \frac{|a_{i,t} - \hat{a}_{i,t}|}{\sigma(i,d(t))}
  \]
- Emit daily `scoresYYYY-MM-DD.csv` for downstream ingestion.[file:1][file:2]

**Implementation**

- **Model architecture** — `src/model/model.py` defines the spatio‑temporal GNN.[cite:11]
- **Training loop** — `src/model/train.py` trains the model using anomaly tensors and `graph.pt`.[cite:11][file:2]
- **Scoring** — `src/model/score.py` loads the trained model and graph, computes residual-based anomaly scores, and writes CSVs to `data/processed/scores/`.[cite:11][file:1]

**Artifacts**

- Checkpoints — stored under `checkpoints/` (gitignored).[cite:3]
- Score CSVs — `data/processed/scores/scoresYYYY-MM-DD.csv` (12,800 zones per date).[file:1]

**Status:** Model trained; score CSVs produced for a 90‑day window and used by API ingest.[cite:11][file:1]

---

## Module 4 — Adaptive Threshold & Feedback Loop

**Goal**  
Maintain per-zone adaptive thresholds \( \theta_i \) based on operator TP/FP feedback to control alert volume.[file:2]

**Responsibilities**

- Store alerts, feedback, thresholds, and score cache in PostgreSQL (NeonDB).
- Ingest daily score CSVs and write alerts above threshold.
- Update per-zone \( \theta_i \) online using precision-based rule and bound it to \([1.5, 4.0]\).[file:1][file:2]

**Implementation**

- **DB & pooling** — `src/api/database.py` + `src/api/db` handle Neon connection pool and table creation.[cite:5][file:1]
- **Tables:**
  - `regionthresholds(regionid, theta, tpcount, fpcount, updated_at)`
  - `alerts(alertid, regionid, alertdate, score, theta_used, chlz, sstz, persistence_days, created_at)`
  - `scorecache(date, zoneid, zscore, chlraw)`
  - `alertfeedback(feedback_id, alert_id, region_id, label, user_id, timestamp)`.[file:1]
- **Ingestion** — `src/api/ingest.py` bulk‑ingests `scoresYYYY-MM-DD.csv` into `alerts` with:
  - bulk fetch of thresholds,
  - one bulk insert for new thresholds,
  - one bulk upsert for alerts (3 DB round-trips per date).[cite:5][file:1]
- **Threshold logic** — `src/api/threshold.py` implements `get_theta`, `update_theta`, `get_all_thresholds`; `feedback.py` wires this into `POST /alerts/{id}/feedback`.[cite:5][cite:6][file:1]

**Status:** Fully wired and tested; ~110k alerts ingested across 90 dates and on‑line recalibration confirmed via `POST /alerts/{id}/feedback` and `GET /thresholds`.[file:1]

---

## Module 5 — FastAPI Backend

**Goal**  
Expose a clean REST API over NeonDB + GNN outputs for the dashboard and NL explain layer.[file:2]

**Tech stack**

- Python (conda env `sentinel-api`).
- FastAPI + Uvicorn.
- PostgreSQL (Neon) with `psycopg2`.
- Pydantic models for request/response schemas.[cite:5]

**Key modules**

- `src/api/main.py` — FastAPI app, startup `init_db`, router registration, static mounting.[cite:5]
- `src/api/models.py` — Pydantic models including alerts, history, explain payloads.[cite:5][file:1]
- `src/api/scorer.py` — CSV reader and in-memory score cache for `/scores`.[cite:5][file:1]

**API routes**

- `src/api/routes/scores.py`:[cite:6]
  - `GET /dates` — list available dates based on score CSVs.
  - `GET /scores?date=YYYY-MM-DD` — returns zone-level scores and top zones; in‑memory caching only.
- `src/api/routes/alerts.py`:[cite:6]
  - `GET /alerts?date=YYYY-MM-DD&top_k=N` — top‑K alerts above thresholds, with risk labels and persistence.
  - `GET /zones/{id}/history?days=30` — 30‑day history from `alerts` or `scorecache`.
- `src/api/routes/zones.py` — `GET /zones` list AOI zones.[cite:6]
- `src/api/routes/feedback.py` — `POST /alerts/{id}/feedback` to log TP/FP and update threshold.[cite:6][file:1]
- `src/api/routes/explain.py` — `POST /explain` NL explain endpoint (see Module 7).[cite:6][file:1]

**Status:** Backend routes implemented and serving the dashboard + explain layer; performance improved via in‑memory score caching.[file:1]

---

## Module 6 — Geospatial Dashboard UI

**Goal**  
Provide a real-time, interactive dashboard that visualizes anomalies, alerts, and history over the Indian EEZ.[file:2]

**Tech stack**

- Static HTML/CSS/JS served from FastAPI.[cite:7]
- Leaflet for mapping.
- Chart.js for time-series sparkline.
- Vanilla JS modules for state and API integration.[cite:8][file:1]

**UI structure** (`src/api/static/index.html`)

- **Top bar:** logo, subtitle, LIVE badge.
- **Main layout:** flex with two regions:
  - Left `#map-container`: Leaflet map + legend.
  - Right `#panel` with sections:
    - Date slider + play button.
    - Selected Zone stats table.
    - 30‑day anomaly history sparkline.
    - Explain Anomaly (Ask AI) section.
    - Top Risk Zones Today alerts list.[cite:7][file:1]

**JS modules**

- `js/heatmap.js` — score→color mapping and risk labels.[cite:8]
- `js/map.js` — loads zones from `/zones`, renders Leaflet layer, zone click → stats + history + explain.[cite:8][file:1]
- `js/timeline.js` — slider + play button → parallel fetch of `/scores` and `/alerts` for a date.[cite:8][file:1]
- `js/history.js` — calls `/zones/{id}/history` and renders Chart.js sparkline under Selected Zone.[file:1][cite:8]
- `js/explain.js` — wires Ask AI button to `/explain` intent resolver.[cite:8][file:1]

**Status:** Functionally complete (map, timeline, alerts, history, explain button); some flex/CSS issues deferred to Module 8.[file:1]

---

## Module 7 — NL Explain Interface

**Goal**  
Provide grounded, closed‑world natural-language explanations for anomalies without allowing hallucinated zones or scores.[file:2]

**Tech stack**

- FastAPI route `src/api/routes/explain.py`.[cite:6]
- LLM runtimes:
  - Ollama (`qwen3` / `llama3` / `mistral`) on LAN RTX 3070 Ti.
  - Groq `llama3-8b-8192` via HTTP API as fallback.[file:1]

**Design**

- **Stage 1 — Intent resolver**  
  Classifies query into `attentionnow`, `zonespecific`, or `trend` via keyword scoring.[file:1]
- **Stage 2 — Context packager**  
  Builds strict JSON context from NeonDB:
  - Current top‑K alerts.
  - Zone-specific 7–30 day history and neighbors.
  - Zone thresholds and persistence.[file:1]
- **Stage 3 — Prompt + validator**  
  Constructs a system prompt instructing:
  - Use only IDs/numbers from JSON.
  - Output exactly 3 bullets.
  - Validator strips any bullet referencing non‑existent zone IDs.[file:1]
- **Fallback behavior**  
  Uses Groq or deterministic bullets from context if Ollama fails.[file:1]

**Status:** Route implemented with intent resolution and context packing; UI wiring present; final E2E explain output verification pending.[file:1]

---

## Module 8 — UI Polish & Resilience

**Goal**  
Make the dashboard visually robust, responsive, and production‑ready.[file:1]

**Planned work**

- Fix flexbox layout so `#panel` never collapses or is pushed off-screen on narrow/zoomed windows.
- Normalize `dashboard.css` risk label classes (`.risk-critical`, `.risk-high`, `.risk-elevated`, `.risk-normal`).[file:1]
- Clean up list styles for Top Risk Zones (remove padding, bullets, align cards).
- Confirm correct AOI centering (Arabian Sea) and zoom in Leaflet.
- Ensure dark-theme contrast and typography consistency.[file:1]

**Status:** Work items identified from debugging sessions; implementation in progress.[file:1]

---

## Tech Stack Summary

**Data & ML (Modules 1–3)**

- Python (conda envs `sentinel-data`, `sentinel-ml`).[file:2]
- Libraries: `xarray`, `netCDF4`, `numpy`, `pandas`, `geopandas`, `shapely`, `torch`, `torch-geometric`, `torch-geometric-temporal`.[file:2]
- Data: CMEMS GlobColour Chl‑a as primary, optional SST.[file:2]

**Backend & API (Modules 4–7)**

- Python (conda env `sentinel-api`).[file:2]
- FastAPI, Uvicorn.[cite:5]
- PostgreSQL (Neon) with `psycopg2`.[cite:5][file:1]
- Pydantic models for API contracts.[cite:5]
- Ollama + Groq for NL explanations.[file:1]

**Frontend (Modules 6–8)**

- Static HTML/CSS/JS served from FastAPI.[cite:7]
- Leaflet for maps.
- Chart.js for time-series sparkline.
- Vanilla JS modules for map, timeline, alerts, history, and explain.[cite:8][file:1]

**Utilities & Tooling**

- PowerShell scripts in `scripts/test_pipeline.ps1` for running pipeline end‑to‑end.[cite:12]
- Helper scripts `scripts/check_zones.py`, `scripts/fix_nan.py` for data sanity checks.[cite:12]

Keep this document updated as modules evolve and Module 8 UI polish is completed.