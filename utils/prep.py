import pandas as pd

def make_tables(df):
    """Prepare summary tables for dashboard visualizations."""

    # --- 1. Timeseries: evolution of stations over time ---
    timeseries = (
        df.groupby(df["date_mise_en_service"].dt.year)
          .size()
          .reset_index(name="Nombre de stations")
          .rename(columns={"date_mise_en_service": "Année"})
          .dropna()
    )

    # --- 2. Regional breakdown: by commune or operator ---
    by_region = (
        df.groupby("nom_operateur")
          .size()
          .reset_index(name="Nombre de stations")
          .sort_values("Nombre de stations", ascending=False)
          .head(15)
    )

    # --- 3. Geographic data ---
    # prefer consolidated latitude/longitude column names
    lat_col = "latitude" if "latitude" in df.columns else ("lat" if "lat" in df.columns else None)
    lon_col = "longitude" if "longitude" in df.columns else ("lon" if "lon" in df.columns else None)
    if lat_col and lon_col:
        geo = df[["nom_station", lat_col, lon_col, "puissance_nominale"]].dropna()
        # normalize column names
        geo = geo.rename(columns={lat_col: "latitude", lon_col: "longitude"})
    else:
        geo = pd.DataFrame(columns=["nom_station", "latitude", "longitude", "puissance_nominale"]) 

    return {
        "timeseries": timeseries,
        "by_region": by_region,
        "geo": geo
    }


def apply_filters(df: pd.DataFrame, communes=None, departments=None, operators=None, date_range=None):
    # Apply commune/department/operator/date filters and return filtered DataFrame.
    df_f = df.copy()

    # Communes: selections may be combined like '75001 — Paris'
    if communes:
        final_mask = pd.Series(False, index=df_f.index)
        for sel in communes:
            sel_mask = pd.Series(False, index=df_f.index)
            if " — " in sel:
                cp_sel, cname_sel = sel.split(" — ", 1)
                if "consolidated_code_postal_str" in df_f.columns:
                    sel_mask = sel_mask | (df_f["consolidated_code_postal_str"] == cp_sel)
                if "consolidated_commune" in df_f.columns:
                    sel_mask = sel_mask | (df_f["consolidated_commune"] == cname_sel)
                if "nom_commune" in df_f.columns:
                    sel_mask = sel_mask | (df_f["nom_commune"] == cname_sel)
            else:
                if "consolidated_code_postal_str" in df_f.columns:
                    sel_mask = sel_mask | (df_f["consolidated_code_postal_str"] == sel)
                if "consolidated_commune" in df_f.columns:
                    sel_mask = sel_mask | (df_f["consolidated_commune"] == sel)
                if "nom_commune" in df_f.columns:
                    sel_mask = sel_mask | (df_f["nom_commune"] == sel)
            final_mask = final_mask | sel_mask
        df_f = df_f[final_mask]

    # Operators
    if operators:
        if "nom_operateur" in df_f.columns:
            df_f = df_f[df_f["nom_operateur"].isin(operators)]

    # Date range
    if date_range and "date_mise_en_service" in df_f.columns:
        start_dt = pd.to_datetime(date_range[0])
        end_dt = pd.to_datetime(date_range[1])
        df_f = df_f[(df_f["date_mise_en_service"] >= start_dt) & (df_f["date_mise_en_service"] <= end_dt)]

    # Departments
    if departments and "dept_code_inferred" in df_f.columns:
        df_f = df_f[df_f["dept_code_inferred"].isin(departments)]

    return df_f


def make_timeseries(df: pd.DataFrame, metric: str = "stations", dedupe_col: str = None):
    # Build annual timeseries for metric; supports deduplication by a station id column.
    df_ts = df.copy()
    if "date_mise_en_service" not in df_ts.columns:
        return pd.DataFrame(columns=["year", metric, "pct_change"])

    df_ts["year"] = df_ts["date_mise_en_service"].dt.year
    df_ts = df_ts[df_ts["year"].notna()].copy()

    if metric == "stations":
        # count distinct station identifiers per year
        id_col = dedupe_col if dedupe_col and dedupe_col in df_ts.columns else ("nom_station" if "nom_station" in df_ts.columns else None)
        if id_col:
            agg = df_ts.groupby("year")[id_col].nunique().reset_index(name="stations")
        else:
            agg = df_ts.groupby("year").size().reset_index(name="stations")
        agg = agg.sort_values("year")
        # cumulative total
        agg["cum_stations"] = agg["stations"].cumsum()
        agg["pct_change"] = agg["cum_stations"].pct_change()
        return agg.rename(columns={"cum_stations": "value"})[["year", "value", "pct_change"]]

    elif metric == "pdc":
        agg = df_ts.groupby("year")["nbre_pdc"].sum().reset_index(name="value")
        agg = agg.sort_values("year")
        agg["pct_change"] = agg["value"].pct_change()
        return agg[["year", "value", "pct_change"]]

    else:  # power
        agg = df_ts.groupby("year")["puissance_nominale"].sum().reset_index(name="value")
        agg = agg.sort_values("year")
        agg["pct_change"] = agg["value"].pct_change()
        return agg[["year", "value", "pct_change"]]

def parse_coords_safe(coord_str):
    try:
        lon, lat = coord_str.strip("()").split(",")
        return float(lat), float(lon)
    except Exception:
        return None, None