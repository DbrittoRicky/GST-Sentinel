# GST-Sentinel – Architecture & Workflow

This document describes the overall system architecture and end‑to‑end workflow of GST‑Sentinel.

---

## System Components

At a high level, GST‑Sentinel consists of four major layers:

1. **Data & ML Layer (Modules 1–3)**  
   - CMEMS ingestion, climatology, and anomaly preparation.[file:2]  
   - Graph construction over Indian EEZ zones.[file:2][cite:10]  
   - CST‑GL‑style ST‑GNN training and scoring to produce daily anomaly CSVs.[file:2][cite:11]

2. **Alerting & Adaptation Layer (Module 4)**  
   - NeonDB-backed alerts, thresholds, feedback, and score cache.[file:1][cite:5]  
   - Ingestion from GNN score CSVs into `alerts` table using optimized bulk upserts.[file:1]

3. **API Layer (Module 5 & 7)**  
   - FastAPI backend exposing `/scores`, `/alerts`, `/zones`, `/thresholds`, `/feedback`, `/explain` endpoints.[cite:5][cite:6]  
   - NL Explain intent resolver + RAG-style context packer.[file:1]

4. **Operator UI Layer (Modules 6–8)**  
   - Leaflet + Chart.js dashboard served from FastAPI static files.[cite:7][cite:8]  
   - Map, date timeline, zone stats, history sparkline, Top Risk Zones sidebar, and Ask AI explain panel.[file:1]

---

## Data Flow Overview

### 1. Offline Data & Model Pipeline

1. **Download**  
   `src/pipeline/download.py` authenticates to CMEMS and downloads GlobColour Chl‑a (and optional SST) NetCDFs for the Indian EEZ.[cite:9][file:2]

2. **Grid & Mask**  
   `src/pipeline/grid.py` defines a coarse grid (≈400 zones) within the AOI and maps 4 km CMEMS pixels to zone IDs.[cite:9][file:2]

3. **Climatology**  
   `src/pipeline/climatology.py` computes multi‑year seasonal mean \( \mu(i,d) \) and std \( \sigma(i,d) \) per zone/day‑of‑year.[cite:9][file:2]

4. **Anomaly Tensor**  
   `src/pipeline/zscore.py` converts daily fields to anomalies \( a_{i,t} \) and builds an anomaly feature tensor \(X[N,T,F]\).[cite:9][file:2]

5. **Correlation Matrix**  
   `src/pipeline/correlation.py` computes zone‑to‑zone Pearson correlation to build `corr_matrix.npy` for graph edges.[cite:9][file:2]

6. **Graph Construction**  
   `src/graph/build_graph.py` creates a PyG `graph.pt` from `zones.geojson`, the anomaly tensor, and correlation matrix.[cite:10][file:2]

7. **Model Training & Scoring**  
   - `src/model/model.py` defines the CST‑GL‑style GNN.[cite:11]  
   - `src/model/train.py` trains on 2019–2022 and validates on 2023.[cite:11]  
   - `src/model/score.py` loads the checkpoint + graph, computes residual-based anomaly scores \( s_{i,t} \), and writes `scoresYYYY-MM-DD.csv` into `data/processed/scores/`.[cite:11][file:1]

### 2. Alerts & Thresholds

8. **Ingestion into NeonDB**  
   - `src/api/ingest.py` scans `data/processed/scores/*.csv` and, for each date, performs:  
     - Bulk fetch of existing thresholds from `regionthresholds`.  
     - Bulk insert default thresholds for new zones.  
     - Bulk upsert into `alerts` with only zones whose score ≥ θ.[cite:5][file:1]  
   - A one‑shot script or PowerShell loop is used to ingest all dates.[file:1]

9. **Thresholds & Feedback**  
   - `src/api/routes/feedback.py` exposes `POST /alerts/{id}/feedback` to record TP/FP.[cite:6][file:1]  
   - `src/api/threshold.py` updates `regionthresholds` per feedback with a precision‑based recalibration rule while clamping within bounds.[cite:5][file:1]

10. **Threshold Inspection**  
    - `GET /thresholds` returns the current table for debugging and UI use.[file:1]

### 3. API & UI Interaction

11. **Scores API**  
    - `src/api/routes/scores.py` uses `get_scores_for_date` from `src/api/scorer.py` to read and cache scores in memory.[cite:5][cite:6]  
    - `GET /scores?date=` returns all zone scores plus top‑N zones for a given date.[file:1]

12. **Alerts & History API**  
    - `GET /alerts?date=&top_k=` returns ranked alerts for Top Risk Zones.[cite:6][file:1]  
    - `GET /zones/{id}/history?days=30` returns per‑zone history for the history sparkline.[cite:6][file:1]

13. **Zones API**  
    - `GET /zones` provides the AOI zones and their IDs for Leaflet.[cite:6][file:1]

14. **Explain API**  
    - `POST /explain` resolves intent, builds context (top alerts or zone history + neighbors), calls Ollama/Groq, validates bullets, and returns explanation.[cite:6][file:1]

15. **Dashboard UI**  
    - `index.html` loads `dashboard.css`, Leaflet, Chart.js, and JS modules `heatmap.js`, `map.js`, `timeline.js`, `explain.js`, `history.js` in that order.[cite:7][cite:8][file:1]  
    - The UI works as a thin client, with all logic delegated to the backend and DB.

---

## Workflow by Persona

### Operator Workflow

1. Open dashboard → map shows current date anomalies, Top Risk Zones sidebar lists live alerts.
2. Drag slider / press Play:
   - UI asks `/scores` and `/alerts` in parallel.
   - Map and sidebar update to that date.[file:1]
3. Click a red/orange zone:
   - Selected Zone panel shows zone ID, anomaly, risk label.
   - HistoryChart calls `/zones/{id}/history` and draws 30‑day sparkline with θ reference line.[file:1]
4. If an alert is false:
   - Click "False Alarm" on that row → `POST /alerts/{id}/feedback` updates threshold.
   - Subsequent runs/dates will apply new θ.[file:1]
5. To understand context:
   - Click "Ask AI" → UI sends `zoneid`, `zscore`, `date`, and optional free‑text query to `/explain`.
   - Backend resolves intent and returns 3 bullets summarizing anomalies.

### Developer Workflow

- **Data/ML iteration:** Run pipeline scripts (`download.py`, `grid.py`, `climatology.py`, `zscore.py`, `correlation.py`, `train.py`, `score.py`) in `sentinel-data`/`sentinel-ml` envs until scores look robust.[cite:9][cite:11][file:2]
- **API iteration:** Use `ingest.py` and Neon DB, plus FastAPI routes, to evolve schema and alerting logic.[cite:5][file:1]
- **UI iteration:** Refine `dashboard.css` and JS modules to improve UX and mobile responsiveness.[cite:7][cite:8][file:1]

---

## Environments & Separation of Concerns

- **`sentinel-data` env:** CMEMS download, preprocessing, climatology, anomaly tensor.[file:2]
- **`sentinel-ml` env:** Graph construction, CST‑GL ST‑GNN training and scoring.[file:2]
- **`sentinel-api` env:** FastAPI backend, NeonDB, dashboard static files, NL explain integration.[file:2][cite:5]

Each env has its own `environment-*.yml` in `/envs` and can be developed independently, with artifacts exchanged via the `data/` directory and `graph.pt`/CSV files.[cite:4][file:2]