import streamlit as st
from utils.viz import plot_power_section, plot_heatmap_and_station_map


def render_deep_dives(filtered_chart):
    """Render deeper analyses: power distributions, scatter by year, heatmap and station map."""
    # Section header
    st.markdown("## Deep dives")

    st.markdown(
        "The power analysis reveals a counter-intuitive trend: the median nominal power dropped from ~150 kW (in 2010) to ~24 kW (in 2025). "
        "This drop strongly suggests a paradigm shift where the massive explosion of lower-power AC destination charging (residential, parking) is pulling the median down, potentially masking a rise in fast-charger (DC) power. It is essential to separate the analysis of the two technologies to assess true long-distance charging capacity."
    )

    # Power-focused visuals
    plot_power_section(filtered_chart)

    st.markdown(
        "Deeper analyses probe practical questions: are newer installs delivering higher power, how skewed is the power distribution, "
        "and where do station clusters form? These views help reveal local hotspots and gaps, informing deployment choices or targeted policies."
    )

    # Power & Technology — Distribution and Evolution (kept in-app previously)
    st.markdown("### Power & Technology — Distribution and Evolution")

    # The section in app.py that renders histogram/boxplot and power-vs-year scatter is left here
    # to reduce top-level complexity. We'll reuse filtered_chart as needed.
    if "puissance_nominale" not in filtered_chart.columns or filtered_chart["puissance_nominale"].dropna().empty:
        st.info("No nominal power data available to show distribution.")
    else:
        # show a small description and allow the app-level control to render the detailed charts
        st.write("Use the controls above to choose histogram/boxplot and inspect trends.")

    # Usage-focused insights (heatmap & map)
    st.markdown(
        "The Heatmap and Map of Charging Stations translate raw numbers into spatial reality, revealing urban hotspots and charging deserts in rural areas. The objective is to highlight geographic gaps where a lack of infrastructure could hinder EV adoption. These spatial views provide a factual basis for guiding targeted subsidy policies and deployment choices."
    )

    # Maps & density
    plot_heatmap_and_station_map(filtered_chart)
