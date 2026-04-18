# 🌊 GST-Sentinel

**Costal Algal Bloom Monitor for the Indian EEZ**

GST-Sentinel is an end-to-end spatio-temporal anomaly detection platform designed to monitor coastal algal blooms across the Indian Exclusive Economic Zone (EEZ). It leverages deep learning (Spatio-Temporal Graph Neural Networks) on satellite imagery data to detect chlorophyll-a anomalies, providing early warnings and actionable insights through a premium, interactive web dashboard.

---

## 🎯 Key Features

- **Data Pipeline**: Automated ingestion and preprocessing of Copernicus Marine Service (CMEMS) GlobColour Chl-a NetCDF datasets, creating normalized anomaly tensors and spatial dependency graphs.
- **AI/ML Engine**: Utilizes PyTorch Geometric to run Spatio-Temporal Graph Neural Networks (ST-GNNs), converting raw satellite data into precise anomaly scores (σ-scores) per zone.
- **Real-Time Backend**: Built on FastAPI and backed by NeonDB (PostgreSQL) for fast, scalable storage of anomaly events, geographical zones, and dynamic threshold configurations.
- **Premium Interactive Dashboard**: A highly polished, "glassmorphic" dark-themed UI serving as the control center:
  - **Dynamic Map**: Interactive Leaflet maps with custom dark Carto tiles, displaying a heat map of chlorophyll anomalies across the Indian Coast.
  - **Zone Analysis**: Click on any map zone to view sparklines and a detailed historical trend graph (with linear regression lines and threshold overlays).
  - **Alert Management**: Prioritized timeline of critical anomaly events with persistence tracking and false-alarm feedback functionality.
  - **AI Explainability**: Built-in chat interface powered by an LLM backend to translate complex ST-GNN anomaly spikes into plain language for analysts.

---

## 🛠️ Technology Stack

### Data & ML Pipeline
* **Python 3**
* **xarray / netCDF4 / pandas / geopandas** - Data handling & geospatial processing
* **PyTorch & PyTorch Geometric** - ST-GNN training and inference

### Backend & Database
* **FastAPI + Uvicorn** - High-performance async API
* **NeonDB (PostgreSQL)** - Serverless relational database
* **Psycopg2** - DB adapter

### Frontend Dashboard
* **HTML5 / Vanilla CSS3 / JavaScript (ES6)**
* **Leaflet.js** - Interactive mapping integration
* **Chart.js (v4.4)** - Multi-dataset charting and sparklines
* *No heavy frontend frameworks—just ultra-optimized, responsive ES6 and native CSS custom properties for styling.*

---

## 🚀 Running the Dashboard Locally

Ensure you have your environment set up and the backend dependencies installed.

**1. Start the Backend API**
Using the `sentinel-api` conda environment (or equivalent virtualenv), run the FastAPI server:
```bash
uvicorn src.api.main:app --reload
```

**2. Access the Dashboard**
Once the server is running, open your browser and navigate to:
[http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📂 Project Architecture

1. **`src/pipeline/`**: Scripts for fetching CMEMS data, gridding, climatology calculation, and generating anomaly tensors.
2. **`src/graph/`**: Scripts for constructing spatial graphs based on correlation matrices.
3. **`src/model/`**: Scripts for ST-GNN training (`train.py`) and inference (`score.py`).
4. **`src/api/`**: The FastAPI backend serving data from NeonDB and handling the static files for the dashboard.
5. **`src/api/static/`**: The frontend UI containing HTML, JS modules (`map.js`, `timeline.js`, `history.js`, `explain.js`), and the main `dashboard.css` stylesheet.

---

## 🎨 UI/UX Philosophy

The GST-Sentinel dashboard recently underwent a thorough UI redesign to achieve an enterprise-grade, premium feel. This includes:
- **Inter & JetBrains Mono typography** for maximum readability of analytical data.
- **Glassmorphism (Backdrop Blurs)** to maintain visual context over the map.
- **Fluid Micro-animations** for button hovers, skeleton loading states, and AI typing effects.
- **Responsive Design** adapting gracefully to various window sizes and split views.
