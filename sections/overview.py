import streamlit as st
import pandas as pd
from utils.viz import plot_timeseries, bar_chart


def render_overview(kpi_df, timeseries, y_col, y_label, filtered_chart, operator_metric: str = "Stations (unique)"):
    """Render KPIs, the main timeseries and top-operators bar chart.

    Parameters
    - kpi_df: DataFrame filtered to 2010+ used to compute KPIs
    - timeseries: aggregated timeseries DataFrame with 'year' and y_col
    - y_col, y_label: series to plot
    - filtered_chart: filtered DataFrame used to compute operator counts
    """
    # Section header
    st.markdown("## Overview")
    # User-provided overview paragraph: infrastructure context
    st.markdown(
        "The French EV infrastructure has reached an impressive scale with 17,120 stations and almost 1.2 million charging points since 2010. "
        "This section establishes the context of rapid growth, emphasizing that the Average Nominal Power (89.3 kW) is the primary quality metric to track. "
        "The key is to compare the Year-over-Year (YOY) station growth rate with EV adoption to assess whether quantity meets demand."
    )
    # KPIs
    c1, c2, c3 = st.columns(3)
    total_stations = kpi_df["nom_station"].nunique() if "nom_station" in kpi_df.columns and not kpi_df.empty else 0
    total_pdc = int(kpi_df["nbre_pdc"].sum()) if "nbre_pdc" in kpi_df.columns and not kpi_df.empty else 0
    avg_power = kpi_df["puissance_nominale"].mean() if "puissance_nominale" in kpi_df.columns and not kpi_df.empty else float("nan")

    c1.metric("Total Stations (2010+)", f"{total_stations:,}")
    c2.metric("Total Charging Points (PDC) (2010+)", f"{total_pdc:,}")
    c3.metric(
        "Avg. Nominal Power (kW) (2010+)",
        f"{avg_power:.1f}" if not pd.isna(avg_power) else "N/A",
    )

    # Timeseries
    plot_timeseries(timeseries, y_col, y_label)

    # Storytelling paragraph for overview (more fluid)
    st.markdown(
        "High‑level metrics and an annotated time series give fast, actionable answers: how many sites and charging points exist, "
        "what typical station power looks like, and whether growth matches capacity. The top-operator view highlights market concentration, "
        "helping to surface whether infrastructure deployment is broadly distributed or driven by a few large providers."
    )

    # Top operators
    st.subheader("Top 15 Operators by Station Count")
    # User-provided paragraph about Top 15 Operators
    st.markdown(
        "The analysis of the Top 15 Operators is crucial for understanding market concentration. While dominance by a few large players ensures deployment efficiency, it raises questions about network resilience and diversity of supply. This view allows regulators to target key market leaders and ensure their deployment strategies cover the entire national territory."
    )
    # Use local aggregation to prepare a small table for the bar chart
    if filtered_chart is None or filtered_chart.empty:
        st.info("No data for operators chart.")
    else:
        # operator_metric controls whether we count unique stations or raw rows
        if operator_metric == "Observations (rows)":
            ops = filtered_chart["nom_operateur"].fillna("UNKNOWN") if "nom_operateur" in filtered_chart.columns else pd.Series(["UNKNOWN"])
            df_ops = ops.value_counts().head(15).reset_index()
            df_ops.columns = ["nom_operateur", "Nombre de stations"]
            bar_chart(df_ops)
        else:
            by_op = (
                filtered_chart.groupby("nom_operateur").agg(**{"Nombre de stations": ("nom_station", "nunique")}).reset_index()
            )
            by_op = by_op.sort_values("Nombre de stations", ascending=False).head(15)
            bar_chart(by_op)
