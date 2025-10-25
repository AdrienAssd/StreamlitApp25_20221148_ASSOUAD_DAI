import streamlit as st


def render_intro():
    """Render the introduction: title, context and data caveats."""

    st.title("Data Storytelling — EV Charging Stations")
    st.markdown("Adrien ASSOUAD | adrien.assouad@efrei.net  ")
    st.caption("Source: Base nationale des IRVE — data.gouv.fr — Open License")
    st.markdown("## Introduction")

    st.markdown(
        "This app explores electric vehicle charging infrastructure (stations, charging points, nominal power). "
        "Filters let you focus by commune, department, operator and commissioning date."
    )
    st.markdown(
        "This dashboard tells a focused story about electric mobility infrastructure: why it matters, how it has evolved, and what the data "
        "reveals about capacity and geographic gaps. Rather than burying conclusions in raw numbers, the app pairs clear metrics with "
        "interactive visuals so each chart directly contributes to an evidence-based narrative that leads from observation to action."
    )

