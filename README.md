# EV Charging Stations — Data Storytelling Dashboard

Adrien ASSOUAD | adrien.assouad@efrei.net

One-line: Interactive Streamlit dashboard exploring EV charging stations in France.


Live demo: https://app25-20221148-asouad-dai.streamlit.app
Repository: https://github.com/AdrienAssd/StreamlitApp25_20221148_ASSOUAD_DAI

## Overview

This small project analyzes the national IRVE dataset (data.gouv.fr) to provide:
- Operator rankings (Top 15 by stations or by observations)
- Time series of deployed stations or charging points (PDC)
- Interactive maps (pydeck) with a fallback to `st.map` when no Mapbox key
- Filters for department/commune/operator and date range

## Quick start

### Prerequisites

- Python 3.8+
- pip

### Install and run

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501

## Minimal project structure

```
app.py                # Streamlit entrypoint
requirements.txt      # Python deps
data/                 # CSV + GeoJSON source files
sections/             # app sections (overview, deep_dives, ...)
utils/                # preprocessing and visualization helpers
assets/               # images / static assets
```

## Data & pipeline

- Source: consolidation IRVE CSV + GeoJSON in `data/`.
- Official dataset: https://www.data.gouv.fr/datasets/base-nationale-des-irve-infrastructures-de-recharge-pour-vehicules-electriques/
- The app cleans and caches data on first run (via `utils.prep`). No manual preprocessing required.
- Recommendation: use `id_station_itinerance` for robust station counts when available.

## Notes

- Map tiles (pydeck) require a Mapbox key set in Streamlit secrets or env var `MAPBOX_API_KEY`.
  If not present the app uses `st.map` and displays a message.
- The sidebar "Metric" selector toggles Top15 behavior:
  - "Stations (unique)": counts unique station identifiers (dedup by `nom_station` by default)
  - "Observations (rows)": counts raw rows; timeseries uses cumulative PDC to avoid year-to-year drops

## Troubleshooting

- If maps show only points (no tiles): add `MAPBOX_API_KEY` to Streamlit Cloud secrets.

## Contact

Adrien ASSOUAD — adrien.assouad@efrei.net

