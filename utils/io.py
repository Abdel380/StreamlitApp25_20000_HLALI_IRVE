# utils/io.py
from __future__ import annotations
import pandas as pd
import re
from typing import Tuple

# Champs potentiels du schéma IRVE (les noms varient selon versions)
LAT_CANDS = ["y_latitude", "latitude", "lat", "ylat"]
LON_CANDS = ["x_longitude", "longitude", "lon", "xlong"]
COORD_CANDS = ["coordonneesxy", "coordonnees_xy", "coordonnees", "geom"]

POWER_CANDS = ["puissance_nominale", "puissance_kw", "puissance"]
STATUS_CANDS = ["etat_pdc", "statut_pdc", "statut"]
ACCESS_CANDS = ["accessibilite", "acces_recharge", "access"]
OPERATOR_CANDS = ["n_operateur", "operateur", "nom_operateur", "id_operateur"]
REGION_CANDS = ["region", "nom_region", "region_administrative"]
DEPT_CANDS = ["departement", "code_departement", "dept"]

def _first_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    low = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in low:
            return low[cand]
    # match loose
    for c in df.columns:
        if any(re.fullmatch(rf".*{cand}.*", c.lower()) for cand in candidates):
            return c
    return None

def _split_coords(series: pd.Series) -> Tuple[pd.Series, pd.Series]:
    # "lon,lat" or "[lon, lat]"
    lon = series.astype(str).str.extract(r"(-?\d+\.?\d*)\s*[, ]")[0]
    lat = series.astype(str).str.extract(r",\s*(-?\d+\.?\d*)")[0]
    return pd.to_numeric(lat, errors="coerce"), pd.to_numeric(lon, errors="coerce")

def load_irve_csv(path: str = "data/irve.csv") -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    # lat/lon
    lat_col = _first_col(df, LAT_CANDS)
    lon_col = _first_col(df, LON_CANDS)
    coord_col = _first_col(df, COORD_CANDS)
    if lat_col and lon_col:
        df["lat"] = pd.to_numeric(df[lat_col], errors="coerce")
        df["lon"] = pd.to_numeric(df[lon_col], errors="coerce")
    elif coord_col:
        lat, lon = _split_coords(df[coord_col])
        df["lat"], df["lon"] = lat, lon
    else:
        df["lat"] = pd.NA
        df["lon"] = pd.NA

    # champs utiles
    df["power_kw"] = pd.to_numeric(
        df[_first_col(df, POWER_CANDS)] if _first_col(df, POWER_CANDS) else pd.NA,
        errors="coerce"
    )

    status_col = _first_col(df, STATUS_CANDS)
    df["status"] = df[status_col].astype(str).str.lower() if status_col else "inconnu"

    access_col = _first_col(df, ACCESS_CANDS)
    df["access"] = df[access_col].astype(str).str.lower() if access_col else "inconnu"

    oper_col = _first_col(df, OPERATOR_CANDS)
    df["operator"] = df[oper_col].astype(str) if oper_col else "inconnu"

    region_col = _first_col(df, REGION_CANDS)
    df["region"] = df[region_col].astype(str) if region_col else "NA"

    dept_col = _first_col(df, DEPT_CANDS)
    df["dept"] = df[dept_col].astype(str) if dept_col else "NA"

    # drop doublons évidents
    df = df.drop_duplicates()

    # filtre géo plausible (France métropolitaine & DROM lax)
    df.loc[~df["lat"].between(-90, 90), ["lat"]] = pd.NA
    df.loc[~df["lon"].between(-180, 180), ["lon"]] = pd.NA
    return df
