import streamlit as st
import pandas as pd
import ast
import os
import json
import pydeck as pdk
import plotly.express as px
from utils.io import load_data
from utils.prep import make_tables, apply_filters, make_timeseries
from utils.viz import (
    bar_chart,
    plot_stations_by_department_map,
    plot_timeseries,
    plot_power_section,
    plot_heatmap_and_station_map,
)
from sections.intro import render_intro
from sections.overview import render_overview
from sections.deep_dives import render_deep_dives
from sections.conclusions import render_conclusions

# --- Page config ---
st.set_page_config(page_title="Data Storytelling: EV Charging Stations", layout="wide")


@st.cache_data(show_spinner=False)
def get_data():
    # load_data() in utils.io now handles date parsing and coordinates (consolidated_longitude/latitude or coordonneesXY)
    df_raw = load_data()

    # Ensure we have normalized latitude/longitude fields (utils.io produces 'latitude'/'longitude')
    if "latitude" not in df_raw.columns and "lat" in df_raw.columns:
        df_raw = df_raw.rename(columns={"lat": "latitude"})
    if "longitude" not in df_raw.columns and "lon" in df_raw.columns:
        df_raw = df_raw.rename(columns={"lon": "longitude"})

    tables = make_tables(df_raw)
    return df_raw, tables


render_intro()

raw, tables = get_data()

# Note: postal code normalization and dept_code inference are now done in utils.io.load_data()

# --- Sidebar filters ---
from datetime import date

# Build commune and operator options separately for clearer filters
# Build combined commune options: prefer entries "<CP> — <Commune>" to avoid duplicates
commune_set = set()
if "consolidated_commune" in raw.columns and "consolidated_code_postal_str" in raw.columns:
    df_cp = raw[["consolidated_code_postal_str", "consolidated_commune"]].dropna()
    for cp, cname in df_cp.drop_duplicates().itertuples(index=False):
        commune_set.add(f"{cp} — {cname}")

# Add commune names that had no postal mapping (avoid duplicates)
if "nom_commune" in raw.columns:
    for cname in raw["nom_commune"].dropna().unique():
        if not any(s.endswith(f" — {cname}") for s in commune_set):
            commune_set.add(cname)

# Add postal-only entries (if any) that weren't paired
if "consolidated_code_postal_str" in raw.columns:
    for cp in raw["consolidated_code_postal_str"].dropna().unique():
        if not any(s.startswith(f"{cp} — ") for s in commune_set):
            commune_set.add(cp)

commune_options = sorted(commune_set)

operator_options = []
if "nom_operateur" in raw.columns:
    operator_options = sorted(list(raw["nom_operateur"].dropna().unique()))

# Build department options from the inferred column
dept_options = sorted([d for d in raw["dept_code_inferred"].dropna().unique()])

with st.sidebar:
    st.header("Filters")

    # Commune selection (supports commune names or postal codes)
    communes = st.multiselect("Commune(s) or Postal code(s) (optional)", commune_options)

    # Department selection (optional) — enter department codes (e.g. '75', '2A', '971')
    departments = st.multiselect("Department(s) (optional)", dept_options)

    # Operator selection
    operators = st.multiselect("Operator(s) (optional)", operator_options)

    # Metric selection
    metric = st.selectbox(
        "Metric",
        [
            "Number of Stations",
            "Number of Charging Points",
            "Total Installed Power (kW)",
        ],
    )

    # Date range filter: fixed scale from 2010-01-01 to today
    min_allowed = date(2010, 1, 1)
    max_allowed = pd.to_datetime("today").date()
    # default to full range
    date_range = st.date_input(
        "Date range",
        value=[min_allowed, max_allowed],
        min_value=min_allowed,
        max_value=max_allowed,
    )

# --- Apply sidebar filters ---
filtered_raw = raw.copy()

# Apply filters using helper in utils.prep
filtered_raw = apply_filters(
    raw,
    communes=communes,
    departments=departments,
    operators=operators,
    date_range=date_range,
)


# KPI (2010+): compute kpi_df and pass to overview for rendering
kpi_df = filtered_raw.copy()
if "date_mise_en_service" in kpi_df.columns:
    kpi_df["year"] = kpi_df["date_mise_en_service"].dt.year
    kpi_df = kpi_df[kpi_df["year"].notna() & (kpi_df["year"] >= 2010)]
else:
    kpi_df = kpi_df.iloc[0:0]

# --- Timeseries table with proper year ---
if "date_mise_en_service" in filtered_raw.columns:
    filtered_raw["year"] = filtered_raw["date_mise_en_service"].dt.year
else:
    filtered_raw["year"] = pd.NA

# For plotting, only keep data from year 2010 onwards
filtered_chart = filtered_raw.copy()
if "year" in filtered_chart.columns:
    # remove rows without a valid year and keep year >= 2010
    filtered_chart = filtered_chart[filtered_chart["year"].notna() & (filtered_chart["year"] >= 2010)]
else:
    filtered_chart = filtered_chart.iloc[0:0]

# Download button: export the currently filtered chart data as CSV
if not filtered_chart.empty:
    try:
        csv_bytes = filtered_chart.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download filtered data (CSV)",
            data=csv_bytes,
            file_name="filtered_irve.csv",
            mime="text/csv",
        )
    except Exception:
        st.info("Filtered data not available for download.")

# Aggregate per year: stations (unique), total PDC, total installed power
timeseries = (
    filtered_chart.groupby("year")
    .agg(
        nom_station=("nom_station", "nunique"),
        nbre_pdc=("nbre_pdc", "sum"),
        puissance_total=("puissance_nominale", "sum"),
    )
    .reset_index()
)
timeseries = timeseries.sort_values("year")

# Choose y column and label based on metric selection
if metric == "Number of Stations":
    # Cumulate stations by year
    timeseries["cum_stations"] = timeseries["nom_station"].fillna(0).cumsum()
    y_col = "cum_stations"
    y_label = "Cumulative Number of Stations"
else:
    if metric == "Number of Charging Points":
        y_col = "nbre_pdc"
        y_label = "Number of Charging Points"
    else:
        y_col = "puissance_total"
        y_label = "Total Installed Power (kW)"

# guard: fill NaN with 0 for aggregates
timeseries[y_col] = timeseries[y_col].fillna(0)

# compute year-over-year pct change (1-year change) on the chosen series
timeseries["pct_change"] = timeseries[y_col].pct_change()

render_overview(kpi_df, timeseries, y_col, y_label, filtered_chart)

render_deep_dives(filtered_chart)

# --- Bar chart ---
st.subheader("Top 15 Operators by Station Count")
tables_filtered = make_tables(filtered_chart)
bar_chart(tables_filtered.get("by_region", pd.DataFrame()))

# --- Power & technology analysis ---
st.markdown("### Power & Technology — Distribution and Evolution")

# Choose chart type for distribution
power_chart_type = st.selectbox(
    "Distribution chart", ["Histogram", "Boxplot"], index=0
)

# Prepare power series (year >= 2010)
power_series = filtered_chart["puissance_nominale"].dropna() if "puissance_nominale" in filtered_chart.columns else pd.Series()
if power_series.empty:
    st.info("No nominal power data available to show distribution.")
else:
    if power_chart_type == "Histogram":
        fig_power = px.histogram(
            filtered_chart,
            x="puissance_nominale",
            nbins=30,
            labels={"puissance_nominale": "Nominal Power (kW)"},
            title="Distribution of Nominal Power (kW)",
        )
        fig_power.update_xaxes(range=[0, 650])
    else:
        fig_power = px.box(
            filtered_chart,
            y="puissance_nominale",
            labels={"puissance_nominale": "Nominal Power (kW)"},
            title="Boxplot of Nominal Power (kW)",
        )
        fig_power.update_yaxes(range=[0, 650])
    fig_power.update_layout(margin=dict(l=40, r=20, t=40, b=40))
    st.plotly_chart(fig_power, use_container_width=True)

    # Scatter: Power vs Year of commissioning
    st.subheader("Nominal Power vs Year of Commissioning")
    scatter_df = filtered_chart.dropna(subset=["puissance_nominale", "year"]).copy()
    if scatter_df.empty:
        st.info("No data to plot Power vs Year.")
    else:
        fig_sc = px.scatter(
            scatter_df,
            x="year",
            y="puissance_nominale",
            hover_data=["nom_station", "nom_operateur"] if "nom_station" in scatter_df.columns and "nom_operateur" in scatter_df.columns else None,
            labels={"puissance_nominale": "Nominal Power (kW)", "year": "Year"},
            title="Nominal Power by Year (points = stations)",
        )

        # median per year
        med = scatter_df.groupby("year")["puissance_nominale"].median().reset_index()
        if not med.empty:
            fig_line = px.line(med, x="year", y="puissance_nominale")
            fig_line.update_traces(line=dict(color="firebrick", width=3), showlegend=False)
            for tr in fig_line.data:
                fig_sc.add_trace(tr)

        fig_sc.update_traces(marker=dict(size=6, opacity=0.6))
        # cap scatter y-axis to 650 kW
        fig_sc.update_yaxes(range=[0, 650])
        fig_sc.update_layout(margin=dict(l=40, r=20, t=40, b=40))
        st.plotly_chart(fig_sc, use_container_width=True)

        # Quick textual insight
        if len(med) >= 2:
            first_val = med.iloc[0]["puissance_nominale"]
            last_val = med.iloc[-1]["puissance_nominale"]
            st.markdown(
                f"**Insight:** Median nominal power increased from ~{int(first_val)} kW (in {int(med.iloc[0]['year'])}) to ~{int(last_val)} kW (in {int(med.iloc[-1]['year'])})."
            )

# heatmap/station map moved to deep_dives

render_conclusions(filtered_chart, raw_df=raw, choropleth_func=plot_stations_by_department_map)
