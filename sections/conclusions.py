import streamlit as st
import pandas as pd


def render_conclusions(filtered_chart, raw_df=None, choropleth_func=None):
    """Render conclusions, limitations and (optionally) a choropleth via the provided function.

    choropleth_func: callable(filtered_chart, metric) - optional function to render department choropleth
    """
    # Section header
    st.markdown("##Data Quality & Limitations")
    # Choropleth explanatory paragraph (user-provided)
    st.markdown(
        "The Choropleth is the critical tool for evaluating territorial equity, measuring regional disparities in infrastructure. Identifying the Top 10 Departments clearly names the deployment leaders. Conversely, the departments at the bottom of the ranking provide the evidence needed to justify political intervention or investment to ensure equitable access to electric mobility for all citizens, regardless of location."
    )

    if choropleth_func is not None:
        try:
            st.markdown("---")
            st.subheader("Choropleth: Stations / PDC by Department")
            chor_metric = st.selectbox("Department metric", ["stations", "pdc"], index=0)
            choropleth_func(filtered_chart, metric=chor_metric)
        except Exception as e:
            st.warning(f"Could not render department choropleth: {e}")

    # Data quality checks
    st.markdown("### Data quality checks")
    st.markdown(
        "Source: data.gouv.fr - https://www.data.gouv.fr/datasets/base-nationale-des-irve-infrastructures-de-recharge-pour-vehicules-electriques/"
    )


    # Totals
    total_raw = len(raw_df) if raw_df is not None else None
    total_filtered = len(filtered_chart) if filtered_chart is not None else 0

    # User-provided Data Quality & Limitations paragraph with dynamic counts
    if total_raw is not None:
        st.markdown(
            f"The credibility of the narrative rests on the cleaning process: the analysis is based on {total_filtered:,} filtered rows from a raw dataset of {total_raw:,} rows, with "
            "zero duplicates." if (raw_df is not None and raw_df.duplicated(keep=False).sum() == 0) else f"{raw_df.duplicated(keep=False).sum():,} duplicates."
        )
    else:
        st.markdown(
            "The credibility of the narrative rests on the cleaning process: the analysis is based on the filtered dataset and upstream raw counts are not provided here. This section lists missing values per column, which is vital for flagging any potential limitations in the analysis (e.g., if Nominal Power is often missing)."
        )

    col1, col2 = st.columns(2)
    with col1:
        if total_raw is None:
            st.markdown("**Total rows (raw):** _not provided_ (pass `raw_df` to the renderer to show this)_")
        else:
            st.markdown(f"**Total rows (raw):** {total_raw:,}")
        st.markdown(f"**Total rows (filtered):** {total_filtered:,}")

    # Missing per column (show counts and percent on the filtered set)
    if total_filtered == 0:
        st.info("No filtered rows available to compute missingness.")
    else:
        st.markdown("**Missing per column (filtered dataset)**:")
        missing = filtered_chart.isna().sum()
        missing = missing[missing >= 0]  # ensure Series
        missing_df = missing.to_frame(name="missing_count")
        missing_df["missing_pct"] = (missing_df["missing_count"] / total_filtered * 100).round(2)
        missing_df = missing_df.sort_values(by="missing_count", ascending=False)
        # Display top columns first; if many columns, show scrollable table
        st.dataframe(missing_df)

    # Duplicates
    try:
        raw_dup_count = raw_df.duplicated(keep=False).sum() if raw_df is not None else None
        filtered_dup_count = filtered_chart.duplicated(keep=False).sum() if filtered_chart is not None else 0
    except Exception:
        raw_dup_count = None
        filtered_dup_count = None

    st.markdown("---")
    st.markdown("**Duplicate rows (any columns):**")
    if raw_dup_count is None:
        st.markdown("Raw duplicate rows (counting all rows that are part of a duplicate group): _not available_")
    else:
        st.markdown(f"Raw duplicate rows (counting all rows that are part of a duplicate group): {int(raw_dup_count):,}")
    st.markdown(f"Filtered duplicate rows: {int(filtered_dup_count):,}")

    st.markdown(
        "_Notes:_ these checks are computed on the dataframe objects provided to the renderer. For upstream provenance and schema-level issues, consider running additional validation steps (unique keys, expected ranges, coordinate validity, and cross-checks with official metadata)."
    )
    st.markdown("# Conclusions")
    # Storytelling paragraph for conclusions (more fluid)
    st.markdown(
        "In closing, the app synthesizes trends and spatial patterns into practical implications: where capacity appears sufficient, "
        "where gaps persist, and which actors or territories may deserve priority attention. The goal is to translate data into clear next steps — "
        "whether policy guidance, deployment priorities, or further monitoring."
    )

    st.markdown("### Key Insights & Next Steps")

    st.success(
        """
#### Key Insights

The analysis of France's EV charging network synthesizes a network that is growing rapidly but facing two main challenges: a technological shift and spatial inequality.

First, a Shifting Power Paradigm is evident: the median nominal power has seen a significant drop (from ≈150 kW to ≈24 kW). This suggests a strategic shift towards the massive deployment of lower-power destination charging (AC). While this boosts plug availability, it necessitates focused, separate monitoring of DC fast-charging capacity for essential long-distance travel.

Second, Geographic Gaps persist. The spatial visualizations (Choropleth/Heatmap) confirm a clear concentration of infrastructure in urban hotspots, leaving many peripheral and rural areas underserved. This territorial disparity is the primary hurdle that prevents equitable nationwide EV adoption.

Finally, the concentration of stations among a few top operators highlights market maturity but demands continued regulatory oversight to ensure deployment remains resilient and covers areas less attractive financially.

#### Next Steps

To address these findings, three concrete actions must follow the data narrative:

- Prioritize Territorial Equity: Authorities must target subsidies and deployment efforts towards the departments identified as having the lowest density of stations/PDC. The goal is to close the geographic gap and ensure equitable national access to charging infrastructure.

- Ensure Capacity Quality: To get a clear picture of service quality, it is essential to filter and track the growth of DC fast-chargers (≥50 kW) separately from AC chargers. This distinguishes service speed from mere plug quantity.

- Maintain Market Oversight: Policy should aim to incentivize operator diversity while monitoring the activity of the top providers. This ensures infrastructure resilience and guarantees consistent deployment in all regions, mitigating risks associated with market concentration.
"""
    )
