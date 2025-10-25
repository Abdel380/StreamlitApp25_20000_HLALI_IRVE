# utils/prep.py
from __future__ import annotations
import pandas as pd
import numpy as np

def categorize_power(kw: float) -> str:
    if pd.isna(kw): return "inconnue"
    if kw < 7: return "<7 kW"
    if kw < 22: return "AC 7–22"
    if kw < 50: return "DC 24–49"
    if kw < 150: return "DC 50–149"
    if kw < 300: return "HPC 150–299"
    return "HPC ≥300"

def make_tables(df: pd.DataFrame, commune_sel: list[str] | None = None, cp_sel: list[str] | None = None):
    d = df.copy()

    # Filtres (si fournis)
    if commune_sel and "consolidated_commune" in d:
        d = d[d["consolidated_commune"].isin(commune_sel)]
    if (not commune_sel) and cp_sel and "consolidated_code_postal" in d:
        d = d[d["consolidated_code_postal"].astype(str).isin([str(x) for x in cp_sel])]

    # Colonnes attendues (créées par cleaning.py)
    pcol = "puissance_kw" if "puissance_kw" in d else "puissance_nominale"
    d[pcol] = pd.to_numeric(d[pcol], errors="coerce")

    d["power_cat"] = d[pcol].apply(categorize_power)

    # Proxy service : fiabilité 'Haute'
    if "fiabilite_estimee" in d:
        d["is_service"] = d["fiabilite_estimee"].astype(str).str.lower().eq("haute")
    else:
        # fallback minimal si jamais cleaning n'a pas tourné
        if "date_maj" in d:
            dm = pd.to_datetime(d["date_maj"], errors="coerce")
            d["is_service"] = (pd.Timestamp.today() - dm).dt.days < 90
        else:
            d["is_service"] = False

    total = len(d)
    pct_service = round(100 * d["is_service"].mean(), 1) if total else 0.0
    pct_fast = round(100 * (d[pcol] >= 50).mean(), 1) if total else 0.0
    kpis = {"total_points": total, "pct_service": pct_service, "pct_fast_dc": pct_fast}

    # Agrégats par commune (si dispo) sinon par CP
    group_col = (
        "departement_label" if "departement_label" in d.columns and d["departement_label"].notna().any()
        else "departement" if "departement" in d.columns and d["departement"].notna().any()
        else "code_postal" if "code_postal" in d.columns
        else None
    )
    if group_col:
        by_place = (d.groupby(group_col, dropna=False)
                      .agg(points=(pcol, "size"),
                           pct_service=("is_service", "mean"),
                           pct_fast=(pcol, lambda s: (s >= 50).mean()))
                      .reset_index())
        by_place["pct_service"] = (100 * by_place["pct_service"]).round(1)
        by_place["pct_fast"] = (100 * by_place["pct_fast"]).round(1)
    else:
        by_place = pd.DataFrame(columns=["place","points","pct_service","pct_fast"])

    power_dist = (d.assign(power_kw_bin=pd.cut(d[pcol],
                       bins=[-np.inf,7,22,50,150,300,np.inf],
                       labels=["<7","7–22","22–50","50–150","150–300","≥300"]))
                    .groupby("power_kw_bin").size().reset_index(name="count"))

    latcol = "lat" if "lat" in d else "consolidated_latitude"
    loncol = "lon" if "lon" in d else "consolidated_longitude"
    geo = d.dropna(subset=[latcol, loncol])[[latcol, loncol, pcol, "power_cat",
                                             "fiabilite_estimee" if "fiabilite_estimee" in d else "is_service",
                                             "nom_operateur",
                                             "consolidated_commune" if "consolidated_commune" in d else "consolidated_code_postal"]]
    geo = geo.rename(columns={latcol: "lat", loncol: "lon", pcol: "puissance_kw"})

    return {"kpis": kpis, "by_commune": by_place, "power_dist": power_dist, "geo": geo}
