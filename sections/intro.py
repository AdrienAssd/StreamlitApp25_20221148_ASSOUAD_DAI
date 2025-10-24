import streamlit as st


def render_intro():
    """Render the introduction: title, context and data caveats."""

    st.title("Data Storytelling — EV Charging Stations")
    st.markdown("Adrien ASSOUAD | adrien.assouad@efrei.net  ")
    st.caption("Source: Base nationale des IRVE — data.gouv.fr — Open License")
    st.markdown("## Introduction")
    # User-provided Introduction & Overview paragraph
    st.markdown(
        "The French EV infrastructure has reached an impressive scale with 17,120 stations and almost 1.2 million charging points since 2010. "
        "This section establishes the context of rapid growth, emphasizing that the Average Nominal Power (89.3 kW) is the primary quality metric to track. "
        "The key is to compare the Year-over-Year (YOY) station growth rate with EV adoption to assess whether quantity meets demand."
    )
    st.markdown(
        "This app explores electric vehicle charging infrastructure (stations, charging points, nominal power). "
        "Filters let you focus by commune, department, operator and commissioning date."
    )
    # Storytelling paragraph: explain intent and narrative flow (more fluid)
    st.markdown(
        "This dashboard tells a focused story about electric mobility infrastructure: why it matters, how it has evolved, and what the data "
        "reveals about capacity and geographic gaps. Rather than burying conclusions in raw numbers, the app pairs clear metrics with "
        "interactive visuals so each chart directly contributes to an evidence-based narrative that leads from observation to action."
    )

