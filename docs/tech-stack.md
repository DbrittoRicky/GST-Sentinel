# GST-Sentinel – Tech Stack

This document summarizes the technologies used across GST‑Sentinel’s pipeline, backend, and frontend.

---

## Languages & Runtimes

- **Python 3** — Primary language for data pipeline, ML model, and backend API.[cite:4][file:2]
- **JavaScript (ES6)** — Frontend dashboard logic (Leaflet, Chart.js, API integration).[cite:8]
- **SQL (PostgreSQL dialect)** — NeonDB schema, queries, and indices.[file:1]
- **PowerShell / Bash** — Utility scripts for orchestrating pipeline and ingestion.[cite:12]

---

## Data & ML Layer (Modules 1–3)

**Environments**

- `sentinel-data` (conda) — CMEMS ingestion + preprocessing.[file:2]
- `sentinel-ml` (conda) — Graph construction + ST‑GNN training and scoring.[file:2]

**Key Libraries**

- **I/O & Arrays**
  - `xarray`, `netCDF4` — NetCDF reading and multi-dimensional arrays for CMEMS products.[file:2]
  - `numpy` — Numeric operations.[file:2]
  - `pandas` — Tabular operations and CSV handling.[file:2]
- **Geospatial**
  - `geopandas`, `shapely` — AOI masking and zone geometries.[file:2]
- **ML & GNN**
  - `torch` — Core deep learning framework.[file:2]
  - `torch-geometric`, `torch-geometric-temporal` — Graph and temporal GNN layers for CST‑GL-like model.[file:2][cite:11]

**External Data**

- CMEMS GlobColour Chl‑a as primary EO input; SST optionally added as a feature.[file:2]

---

## Alerting & API Layer (Modules 4–7)

**Environment**

- `sentinel-api` (conda) — FastAPI backend, NeonDB connectivity, NL explain integration.[file:2]

**Backend Frameworks & Libraries**

- **FastAPI** — High-performance async web framework for `/scores`, `/alerts`, `/zones`, `/explain`, etc.[cite:5]
- **Uvicorn** — ASGI server used to run the API (`uvicorn src.api.main:app --reload`).[cite:5][file:1]
- **Pydantic** — Data validation for request/response models in `src/api/models.py`.[cite:5]

**Database**

- **PostgreSQL (NeonDB)** — Managed cloud Postgres used as the system of record for alerts and thresholds.[file:1]
- **Client** — `psycopg2` with connection pooling in `src/api/database.py`.[cite:5][file:1]
- **Schema objects:**
  - `regionthresholds` for adaptive thresholds.
  - `alerts` for daily anomalous events per zone/date.
  - `scorecache` for potential score caching.
  - `alertfeedback` for TP/FP audit trail.[file:1]

**NL Explain**

- **Ollama** — Local inference server for Qwen3 / Llama 3 / Mistral small models.[file:1]
- **Groq API** — Fallback inference for Llama‑3 on Groq’s cloud.[file:1]
- **HTTP client** — `httpx` used in `src/api/routes/explain.py` to talk to these endpoints.[file:1]

---

## Frontend / Dashboard Layer (Modules 6–8)

**Hosting**

- Static assets under `src/api/static/` are served by FastAPI’s `StaticFiles` mount in `src/api/main.py`.[cite:5][cite:7]

**HTML & CSS**

- `index.html` — Main dashboard layout with top bar, map container, and right-hand control panel.[cite:7][file:1]
- `css/dashboard.css` — Custom styling for top bar, layout, map, panel, and typography.[cite:7][file:1]

**JavaScript Modules**

- **Mapping & Visuals**
  - `Leaflet` (CDN: `https://unpkg.com/leaflet/...`) used to render the basemap and zone polygons.[cite:7]
  - `Chart.js` (CDN: `https://cdn.jsdelivr.net/npm/chart.js@4...`) used for the 30‑day anomaly sparkline.[file:1]

- **App Logic**
  - `js/heatmap.js` — Risk color scale and `riskLabel` function.[cite:8]
  - `js/map.js` — Map initialization, zone layer rendering, zone click handler, linking selected zone to stats/history/explain.[cite:8][file:1]
  - `js/timeline.js` — Slider and autoplay logic fetching `/scores` and `/alerts` for selected date.[cite:8][file:1]
  - `js/history.js` — HistoryChart module calling `/zones/{id}/history` and drawing Chart.js sparkline.[file:1][cite:8]
  - `js/explain.js` — Explain button wiring, sending `zoneid`, `zscore`, `date`, and `query` to `/explain` and rendering bullets.[cite:8][file:1]

**UI Pattern**

- Single-page dashboard with:
  - map + legend,
  - timeline slider,
  - selected zone details,
  - history chart,
  - explain panel,
  - alert list.[cite:7][file:1]

---

## Scripts & Tooling

- `scripts/test_pipeline.ps1` — Powershell script to orchestrate pipeline runs end‑to‑end for testing.[cite:12][file:1]
- `scripts/check_zones.py` — Checks zone consistency and helps debug misaligned geometries.[cite:12]
- `scripts/fix_nan.py` — Cleans NaNs or invalid values in intermediate data files.[cite:12][file:1]

---

## Deployment & Ops (Current State)

- **Local dev**  
  - Conda envs for data, ML, and API.
  - Uvicorn for API.
  - NeonDB for Postgres with free tier constraints (cold starts, limited connections).[file:1]

- **Runtime expectations**
  - Data/ML modules run offline; score CSVs are treated as an upstream artifact for the API layer.
  - API and UI can run on a modest server, with heavy compute (GNN and Ollama) offloaded to a GPU machine on the same LAN.[file:1]

This stack is intentionally minimal but production-oriented: Python/FastAPI + Postgres for backend reliability, and Leaflet/Chart.js for a lightweight, fast dashboard.