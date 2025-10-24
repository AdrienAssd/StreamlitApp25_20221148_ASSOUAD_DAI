import pandas as pd
import os
import ast


def load_data():
    # Load and preprocess the IRVE dataset: prefer consolidation CSV, parse coords/dates, cast numerics.

    # --- Path: prefer processed parquet, else look in data/raw for the consolidation CSV ---
    cwd = os.getcwd()
    # prefer a processed parquet for speed if present
    p_parquet = os.path.join(cwd, "data", "processed", "irve.parquet")
    csv_paths = [
        os.path.join(cwd, "data", "raw", "consolidation-etalab-schema-irve-statique-v-2.3.1-20251024.csv"),
        os.path.join(cwd, "data", "consolidation-etalab-schema-irve-statique-v-2.3.1-20251024.csv"),
        os.path.join(cwd, "consolidation-etalab-schema-irve-statique-v-2.3.1-20251024.csv"),
    ]

    # try parquet first
    if os.path.exists(p_parquet):
        df = pd.read_parquet(p_parquet)
    else:
        # try CSV candidate paths in order
        csv_found = None
        for p in csv_paths:
            if os.path.exists(p):
                csv_found = p
                break

        if csv_found is None:
            # try to discover a likely CSV in data/ or data/raw/ (look for keywords)
            candidates = []
            data_raw_dir = os.path.join(cwd, "data", "raw")
            data_dir = os.path.join(cwd, "data")
            for d in (data_raw_dir, data_dir):
                if os.path.isdir(d):
                    for fname in os.listdir(d):
                        if fname.lower().endswith(".csv"):
                            candidates.append(os.path.join(d, fname))

            # prefer filenames that include typical keywords
            keywords = ("consolid", "etalab", "irve")
            for c in candidates:
                ln = os.path.basename(c).lower()
                if any(k in ln for k in keywords):
                    csv_found = c
                    break

            # fallback to the first CSV in data dirs
            if csv_found is None and candidates:
                csv_found = candidates[0]

        if csv_found is None:
            tried = "', '".join(csv_paths)
            raise FileNotFoundError(
                f"Expected consolidation CSV at one of ('{tried}') or processed parquet at '{p_parquet}' not found. Tried to discover CSVs in data/ but found: {candidates}"
            )

        # --- Load CSV ---
        df = pd.read_csv(csv_found, sep=",", encoding="utf-8", low_memory=False)

    # --- Coordinates: prefer consolidated_longitude/latitude, else parse coordonneesXY ---
    if "consolidated_longitude" in df.columns and "consolidated_latitude" in df.columns:
        df["longitude"] = pd.to_numeric(df["consolidated_longitude"], errors="coerce")
        df["latitude"] = pd.to_numeric(df["consolidated_latitude"], errors="coerce")
    elif "coordonneesXY" in df.columns:
        def parse_coords_safe(coord):
            """Handle strings like "[lon,lat]" or "(lon,lat)" or simple 'lon,lat'. Return (lon, lat) or (None, None)."""
            if pd.isna(coord):
                return None, None
            if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                try:
                    return float(coord[0]), float(coord[1])
                except Exception:
                    return None, None
            if isinstance(coord, str):
                try:
                    # try literal_eval first (handles [lon,lat])
                    val = ast.literal_eval(coord)
                    if isinstance(val, (list, tuple)) and len(val) >= 2:
                        return float(val[0]), float(val[1])
                except Exception:
                    pass
                # fallback: split by comma
                if "," in coord:
                    parts = coord.strip("()[] ").split(",")
                    if len(parts) >= 2:
                        try:
                            return float(parts[0]), float(parts[1])
                        except Exception:
                            return None, None
            return None, None

        coords = df["coordonneesXY"].apply(parse_coords_safe)
        df["longitude"] = coords.apply(lambda x: x[0])
        df["latitude"] = coords.apply(lambda x: x[1])

    # --- Clean date columns ---
    if "date_mise_en_service" in df.columns:
        df["date_mise_en_service"] = pd.to_datetime(df["date_mise_en_service"], errors="coerce")
    if "date_maj" in df.columns:
        df["date_maj"] = pd.to_datetime(df["date_maj"], errors="coerce")

    # --- Numeric casts ---
    if "puissance_nominale" in df.columns:
        df["puissance_nominale"] = pd.to_numeric(df["puissance_nominale"], errors="coerce")
    if "nbre_pdc" in df.columns:
        df["nbre_pdc"] = pd.to_numeric(df["nbre_pdc"], errors="coerce").fillna(0)

    # --- Normalize consolidated postal code as string (e.g. 75001.0 -> '75001') ---
    if "consolidated_code_postal" in df.columns:
        try:
            tmp = pd.to_numeric(df["consolidated_code_postal"], errors="coerce")
            df["consolidated_code_postal_str"] = tmp.where(tmp.notna(), None).apply(lambda x: str(int(x)) if pd.notna(x) else None)
        except Exception:
            df["consolidated_code_postal_str"] = df["consolidated_code_postal"].astype(str).where(df["consolidated_code_postal"].notna(), None)
    else:
        df["consolidated_code_postal_str"] = None

    # --- Infer department code (preserve 2A/2B and support DOM 971..976) ---
    def _infer_dept(row):
        try:
            if "code_insee_commune" in row and pd.notna(row["code_insee_commune"]):
                vinsee = str(row["code_insee_commune"]).strip()
                if len(vinsee) >= 2:
                    # preserve letters like 2A/2B
                    prefix = vinsee[:2]
                    return prefix
        except Exception:
            pass
        # fallback to postal code
        for c in ("consolidated_code_postal_str", "consolidated_code_postal", "code_postal", "code_postal_commune"):
            if c in row and pd.notna(row[c]):
                p = str(row[c]).strip()
                if p.startswith(("97", "98")) and len(p) >= 3:
                    return p[:3]
                if len(p) >= 2:
                    return p[:2].zfill(2)
        return None

    df["dept_code_inferred"] = df.apply(_infer_dept, axis=1)

    return df
