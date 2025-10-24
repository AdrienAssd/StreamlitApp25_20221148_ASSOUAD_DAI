import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json


def _cap_axis_range(fig, axis: str = "y", low: int = 0, high: int = 650):
    """Cap axis range on a Plotly figure. axis should be 'x' or 'y'."""
    if axis == "y":
        try:
            fig.update_yaxes(range=[low, high])
        except Exception:
            pass
    else:
        try:
            fig.update_xaxes(range=[low, high])
        except Exception:
            pass


def _add_median_line(fig, df: pd.DataFrame, x: str = "year", y: str = "puissance_nominale"):
    """Add median-per-x line to a Plotly figure if data available."""
    med = df.groupby(x)[y].median().reset_index()
    if not med.empty:
        line = px.line(med, x=x, y=y)
        for tr in line.data:
            fig.add_trace(tr)


def _downsample_df(df: pd.DataFrame, max_rows: int):
    """Return a downsampled dataframe of at most max_rows (random_state stable)."""
    if df is None:
        return df
    if len(df) <= max_rows:
        return df
    return df.sample(n=max_rows, random_state=42)


def _build_tooltip_html(df: pd.DataFrame, fields_map: dict):
    """Return tooltip HTML built from fields_map where keys are column names and values are label strings."""
    parts = []
    for col, label in fields_map.items():
        if col in df.columns:
            parts.append(f"<b>{label}:</b> {{{col}}}")
    parts.extend(["<b>Lat:</b> {latitude}", "<b>Lon:</b> {longitude}"])
    return "<br>".join(parts)


def line_chart(df):
    st.line_chart(df, x="Année", y="Nombre de stations")


def bar_chart(df):
        # Render a bar chart of top operators (expects nom_operateur and Nombre de stations).
    if df is None or df.empty:
        st.info("No data to display.")
        return

    fig = px.bar(
        df,
        x="nom_operateur",
        y="Nombre de stations",
        labels={"nom_operateur": "Operator", "Nombre de stations": "Number of Stations"},
    )

    # Rotate x-axis labels by 45 degrees and add margins so labels don't get cut off
    fig.update_layout(
        xaxis_tickangle=-45,
        xaxis_tickfont=dict(size=10),
        margin=dict(l=40, r=20, t=40, b=120),
        yaxis_title="Number of Stations",
    )

    st.plotly_chart(fig, use_container_width=True)


def map_chart(df):
    # Streamlit’s built-in map for simplicity
    st.map(df.rename(columns={"lat": "latitude", "lon": "longitude"}))


def plot_stations_by_department_map(df: pd.DataFrame, metric: str = "stations"):
    # Choropleth of stations or PDC by department (infers dept codes from INSEE or postal codes).

    st.subheader("Geographic distribution — Charging stations by department")

    if df is None or df.empty:
        st.info("No data available to build a department map.")
        return

    df_map = df.copy()

    # Prefer INSEE-derived department if available (preserves 2A/2B)
    def infer_dept(row):
        # Try code_insee_commune first
        try:
            if "code_insee_commune" in row and pd.notna(row["code_insee_commune"]):
                v = str(row["code_insee_commune"]).strip()
                if len(v) >= 2:
                    prefix = v[:2]
                    # INSEE may contain 2A/2B
                    if prefix.isalpha() or ("A" in prefix or "B" in prefix):
                        return prefix
                    return prefix
        except Exception:
            pass

        # Fallback to postal code
        postal = None
        for col in ("consolidated_code_postal", "code_postal", "code_postal_commune"):
            if col in row and pd.notna(row[col]):
                postal = str(row[col]).strip()
                break

        if postal:
            # DOM/TOM often start with 97 or 98 and use 3-digit department codes
            if postal.startswith(("97", "98")) and len(postal) >= 3:
                return postal[:3]
            # Otherwise metropolitan departments are first two digits
            if len(postal) >= 2:
                return postal[:2].zfill(2)

        return None

    df_map["dept_code"] = df_map.apply(infer_dept, axis=1)

    # Valid department codes: metropolitan 01-95, Corsica 2A/2B, overseas 971-978, 975 etc.
    valid_depts = [f"{i:02d}" for i in range(1, 96)] + ["2A", "2B"] + [str(x) for x in range(971, 980)]
    df_map = df_map[df_map["dept_code"].isin(valid_depts)]

    if df_map.empty:
        st.info("No valid department information could be inferred from the data.")
        return

    # Aggregate counts per department
    if metric == "pdc" and "nbre_pdc" in df_map.columns:
        dept_counts = df_map.groupby("dept_code")["nbre_pdc"].sum().reset_index()
        dept_counts.columns = ["dept_code", "pdc"]
        value_col = "pdc"
        label = "Number of Charging Points (PDC)"
    else:
        # Default: count distinct stations if possible, else count rows
        if "nom_station" in df_map.columns:
            dept_counts = df_map.groupby("dept_code")["nom_station"].nunique().reset_index()
            dept_counts.columns = ["dept_code", "stations"]
        else:
            dept_counts = df_map.groupby("dept_code").size().reset_index(name="stations")
        value_col = "stations"
        label = "Number of Stations"

    # Add department names (basic map, missing ones will show the code)
    dept_names = {
        '01': 'Ain', '02': 'Aisne', '03': 'Allier', '04': 'Alpes-de-Haute-Provence',
        '05': 'Hautes-Alpes', '06': 'Alpes-Maritimes', '07': 'Ardèche', '08': 'Ardennes',
        '09': 'Ariège', '10': 'Aube', '11': 'Aude', '12': 'Aveyron', '13': 'Bouches-du-Rhône',
        '14': 'Calvados', '15': 'Cantal', '16': 'Charente', '17': 'Charente-Maritime',
        '18': 'Cher', '19': 'Corrèze', '21': "Côte-d'Or", '22': "Côtes-d'Armor",
        '23': 'Creuse', '24': 'Dordogne', '25': 'Doubs', '26': 'Drôme', '27': 'Eure',
        '28': 'Eure-et-Loir', '29': 'Finistère', '30': 'Gard', '31': 'Haute-Garonne',
        '32': 'Gers', '33': 'Gironde', '34': 'Hérault', '35': 'Ille-et-Vilaine',
        '36': 'Indre', '37': 'Indre-et-Loire', '38': 'Isère', '39': 'Jura', '40': 'Landes',
        '41': 'Loir-et-Cher', '42': 'Loire', '43': 'Haute-Loire', '44': 'Loire-Atlantique',
        '45': 'Loiret', '46': 'Lot', '47': 'Lot-et-Garonne', '48': 'Lozère', '49': 'Maine-et-Loire',
        '50': 'Manche', '51': 'Marne', '52': 'Haute-Marne', '53': 'Mayenne', '54': 'Meurthe-et-Moselle',
        '55': 'Meuse', '56': 'Morbihan', '57': 'Moselle', '58': 'Nièvre', '59': 'Nord',
        '60': 'Oise', '61': 'Orne', '62': 'Pas-de-Calais', '63': "Puy-de-Dôme",
        '64': 'Pyrénées-Atlantiques', '65': 'Hautes-Pyrénées', '66': 'Pyrénées-Orientales',
        '67': 'Bas-Rhin', '68': 'Haut-Rhin', '69': 'Rhône', '70': 'Haute-Saône',
        '71': 'Saône-et-Loire', '72': 'Sarthe', '73': 'Savoie', '74': 'Haute-Savoie',
        '75': 'Paris', '76': 'Seine-Maritime', '77': 'Seine-et-Marne', '78': 'Yvelines',
        '79': 'Deux-Sèvres', '80': 'Somme', '81': 'Tarn', '82': 'Tarn-et-Garonne',
        '83': 'Var', '84': 'Vaucluse', '85': 'Vendée', '86': 'Vienne', '87': 'Haute-Vienne',
        '88': 'Vosges', '89': 'Yonne', '90': 'Territoire de Belfort', '91': 'Essonne',
        '92': 'Hauts-de-Seine', '93': 'Seine-Saint-Denis', '94': 'Val-de-Marne', '95': "Val-d'Oise",
        '2A': 'Corse-du-Sud', '2B': 'Haute-Corse',
        '971': 'Guadeloupe', '972': 'Martinique', '973': 'Guyane', '974': 'La Réunion', '976': 'Mayotte',
        '975': 'Saint-Pierre-et-Miquelon', '977': 'Saint-Barthélemy', '978': 'Saint-Martin'
    }

    dept_counts['dept_name'] = dept_counts['dept_code'].map(dept_names).fillna(dept_counts['dept_code'])

    # Prefer a local simplified GeoJSON if present under data/geo, else fall back to remote
    local_geo = os.path.join(os.getcwd(), "data", "geo", "departements_simplified.geojson")
    if os.path.exists(local_geo):
        try:
            with open(local_geo, "r", encoding="utf-8") as fh:
                geojson_obj = json.load(fh)
        except Exception:
            geojson_obj = None
    else:
        geojson_obj = None

    # Remote fallback
    remote_geo = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"
    geojson_source = geojson_obj if geojson_obj is not None else remote_geo

    # If the metric is PDC, cap the color scale at 10k to avoid a too-large range
    choropleth_kwargs = dict(
        locations="dept_code",
        geojson=geojson_source,
        featureidkey="properties.code",
        color=value_col,
        hover_name="dept_name",
        hover_data={"dept_code": True, value_col: ":,"},
        color_continuous_scale="YlOrRd",
        labels={value_col: label},
        title=f"{label} by Department",
    )

    if value_col == "pdc":
        choropleth_kwargs["range_color"] = (0, 10000)

    fig = px.choropleth(dept_counts, **choropleth_kwargs)

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(height=600, margin={"r": 0, "t": 30, "l": 0, "b": 0})

    st.plotly_chart(fig, use_container_width=True)

    # Show top 10 departments
    st.markdown(f"**Top 10 Departments by {label}:**")
    top_10 = dept_counts.nlargest(10, value_col)[["dept_code", "dept_name", value_col]]
    top_10[value_col] = top_10[value_col].apply(lambda x: f"{int(x):,}")
    st.dataframe(top_10.rename(columns={value_col: label}), hide_index=True, use_container_width=True)


def plot_timeseries(timeseries: pd.DataFrame, y_col: str, y_label: str):
    """Render the evolution line chart with year-over-year annotations and optional 2021-2023 band.

    timeseries: dataframe with columns ['year', y_col, 'pct_change']
    """
    import plotly.express as px

    st.subheader("Evolution of Stations Over Time")
    st.caption("Note: the percentage shown above each year is the year-over-year change (compared to the previous year).")

    if timeseries is None or timeseries.empty:
        st.info("No timeseries data available for the selected filters.")
        return

    fig = px.line(
        timeseries,
        x="year",
        y=y_col,
        markers=True,
        labels={y_col: y_label, "year": "Year"},
        title=f"Evolution — {y_label}",
    )
    fig.update_xaxes(tickformat="d")

    years_present = set(timeseries["year"].dropna().astype(int).tolist())
    if {2021, 2022, 2023}.intersection(years_present):
        try:
            fig.add_vrect(x0=2021, x1=2023, fillcolor="LightSalmon", opacity=0.12, line_width=0)
        except Exception:
            pass

    # annotate pct change above each point
    for _, row in timeseries.iterrows():
        pct = row.get("pct_change", None)
        if pd.isna(pct):
            continue
        year = int(row["year"])
        value = float(row[y_col])
        pct_text = f"{pct * 100:+.0f}%"
        if pct > 0.4:
            bgcolor = "rgba(30,144,255,0.95)"
            font_color = "white"
            font_size = 11
        else:
            bgcolor = "rgba(255,255,255,0.8)"
            font_color = "black"
            font_size = 10
        fig.add_annotation(
            x=year,
            y=value,
            text=pct_text,
            showarrow=False,
            yshift=12,
            bgcolor=bgcolor,
            bordercolor="rgba(0,0,0,0.1)",
            font=dict(size=font_size, color=font_color),
        )

    st.plotly_chart(fig, use_container_width=True)


def plot_power_section(filtered_chart: pd.DataFrame):
    """Render the power distribution, boxplots and scatter trends (keeps same layout/limits as before)."""
    import plotly.express as px

    st.subheader("Power — distribution & trend")

    if filtered_chart is None or filtered_chart.empty or "puissance_nominale" not in filtered_chart.columns:
        st.info("No power data available to show distribution.")
        return

    # Prepare power dataframe (only entries with nominal power)
    power_df = filtered_chart[["puissance_nominale", "year"]].copy()
    power_df = power_df[power_df["puissance_nominale"].notna()]

    if power_df.empty:
        st.info("No power data available to show distribution.")
        return

    c1, c2 = st.columns(2)
    with c1:
        fig_hist = px.histogram(
            power_df,
            x="puissance_nominale",
            nbins=40,
            labels={"puissance_nominale": "Nominal Power (kW)"},
            title="Distribution of Nominal Power",
        )
        _cap_axis_range(fig_hist, axis="x", low=0, high=650)
        st.plotly_chart(fig_hist, use_container_width=True)

    with c2:
        fig_box = px.box(
            power_df,
            y="puissance_nominale",
            points="outliers",
            labels={"puissance_nominale": "Nominal Power (kW)"},
            title="Boxplot of Nominal Power",
        )
        _cap_axis_range(fig_box, axis="y", low=0, high=650)
        st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("Power vs Year — are newer stations more powerful?")
    scatter_df = power_df.copy()
    fig_scatter = px.scatter(
        scatter_df,
        x="year",
        y="puissance_nominale",
        opacity=0.6,
        labels={"year": "Year", "puissance_nominale": "Nominal Power (kW)"},
        title="Power per Station Over Time",
    )

    _add_median_line(fig_scatter, scatter_df, x="year", y="puissance_nominale")
    _cap_axis_range(fig_scatter, axis="y", low=0, high=650)
    st.plotly_chart(fig_scatter, use_container_width=True)


def plot_heatmap_and_station_map(filtered_chart: pd.DataFrame):
    """Render the heatmap and station scatter using pydeck (keeps payload protections)."""
    import pydeck as pdk

    st.subheader("Usage-focused insights")

    # Heatmap: density of stations
    if not filtered_chart.empty and "latitude" in filtered_chart.columns and "longitude" in filtered_chart.columns:
        st.markdown("**Heatmap — density of stations**")

        map_src = filtered_chart.dropna(subset=["latitude", "longitude"]).loc[:, ["latitude", "longitude"]].copy()
        map_src["lat_r"] = map_src["latitude"].round(4)
        map_src["lon_r"] = map_src["longitude"].round(4)
        agg = map_src.groupby(["lat_r", "lon_r"]).size().reset_index(name="count")
        agg = agg.rename(columns={"lat_r": "latitude", "lon_r": "longitude"})

        MAX_HEAT_POINTS = 20000
        agg = agg.sort_values("count", ascending=False)
        agg = _downsample_df(agg, MAX_HEAT_POINTS)

        heat = pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v10",
            initial_view_state=pdk.ViewState(
                latitude=agg["latitude"].mean() if not agg.empty else 46.6,
                longitude=agg["longitude"].mean() if not agg.empty else 2.4,
                zoom=6,
                pitch=0,
            ),
            layers=[
                pdk.Layer(
                    "HeatmapLayer",
                    data=agg,
                    get_position="[longitude, latitude]",
                    weight="count",
                    radius_pixels=60,
                )
            ],
        )
        st.pydeck_chart(heat)
    else:
        st.info("No data for heatmap.")

    # Map of stations (scatter)
    st.subheader("Map of Charging Stations")
    if not filtered_chart.empty and "latitude" in filtered_chart.columns and "longitude" in filtered_chart.columns:
        scatter_src = filtered_chart.dropna(subset=["latitude", "longitude"]).loc[:, ["latitude", "longitude"]].copy()

        for col in ("nom_station", "nom_operateur"):
            if col in filtered_chart.columns:
                scatter_src[col] = filtered_chart.loc[scatter_src.index, col].astype(str).str.slice(0, 80)
        if "nbre_pdc" in filtered_chart.columns:
            scatter_src["nbre_pdc"] = pd.to_numeric(filtered_chart.loc[scatter_src.index, "nbre_pdc"], errors="coerce").fillna(0).astype(int)
        if "puissance_nominale" in filtered_chart.columns:
            scatter_src["puissance_nominale"] = pd.to_numeric(filtered_chart.loc[scatter_src.index, "puissance_nominale"], errors="coerce").round(0)

        MAX_SCATTER_POINTS = 10000
        scatter_src = _downsample_df(scatter_src, MAX_SCATTER_POINTS)

        fields_map = {"nom_station": "Station", "nom_operateur": "Operator", "nbre_pdc": "PDC", "puissance_nominale": "Power (kW)"}
        tooltip_html = _build_tooltip_html(scatter_src, fields_map)

        st.pydeck_chart(
            pdk.Deck(
                map_style="mapbox://styles/mapbox/light-v10",
                initial_view_state=pdk.ViewState(
                    latitude=scatter_src["latitude"].mean(),
                    longitude=scatter_src["longitude"].mean(),
                    zoom=6,
                    pitch=0,
                ),
                layers=[
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=scatter_src,
                        get_position="[longitude, latitude]",
                        get_color="[200, 30, 0, 160]",
                        get_radius=500,
                        pickable=True,
                        auto_highlight=True,
                    )
                ],
                tooltip={
                    "html": tooltip_html,
                    "style": {"backgroundColor": "steelblue", "color": "white", "fontSize": "12px", "padding": "5px"},
                },
            )
        )
    else:
        st.info("No stations found for the selected filters.")
