import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Overview", layout="wide")

@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    for c in ["date_maj", "date_mise_en_service"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in ["is_dc", "access_24_7", "est_publique", "reservation"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().str.lower().isin(["1", "true", "vrai", "oui", "yes"])
    for c in ["puissance_kw", "puissance_nominale", "latitude", "longitude", "code_postal"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["categorie_puissance", "nom_operateur", "departement"]:
        if c in df.columns and df[c].dtype == object:
            df[c] = df[c].astype("category")
    return df

def ensure_date_series(df: pd.DataFrame) -> pd.Series:
    if "date_mise_en_service" in df.columns and df["date_mise_en_service"].notna().any():
        base = df["date_mise_en_service"]
    elif "date_maj" in df.columns and df["date_maj"].notna().any():
        base = df["date_maj"]
    else:
        return pd.Series(pd.NaT, index=df.index, name="date_any")
    return base

def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")
    depts = sorted(df["departement"].dropna().unique().tolist()) if "departement" in df else []
    sel_depts = st.sidebar.multiselect("Departments", depts, default=depts)
    ops = sorted(df["nom_operateur"].dropna().unique().tolist()) if "nom_operateur" in df else []
    default_ops = ops if len(ops) <= 15 else ops[:15]
    sel_ops = st.sidebar.multiselect("Operators", ops, default=default_ops)
    dc_choice = st.sidebar.radio("Current type", ["All", "DC", "AC"], index=0, horizontal=True)
    only_247 = st.sidebar.checkbox("Only 24/7 access", value=False)
    date_series = ensure_date_series(df)
    start_date = end_date = None
    if date_series.notna().any():
        min_date = pd.to_datetime(date_series.min())
        max_date = pd.to_datetime(date_series.max())
        start_date, end_date = st.sidebar.date_input(
            "Period (installations)",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )
    p_range = None
    if "puissance_kw" in df.columns and df["puissance_kw"].notna().any():
        pmax = float(np.nanmax(df["puissance_kw"]))
        p_range = st.sidebar.slider(
            "Power (kW)",
            min_value=0.0,
            max_value=max(1.0, round(pmax, 1)),
            value=(0.0, max(1.0, round(pmax, 1))),
        )
    f = df.copy()
    if sel_depts and "departement" in f.columns:
        f = f[f["departement"].isin(sel_depts)]
    if sel_ops and "nom_operateur" in f.columns:
        f = f[f["nom_operateur"].isin(sel_ops)]
    if dc_choice != "All" and "is_dc" in f.columns:
        f = f[f["is_dc"] == (dc_choice == "DC")]
    if only_247 and "access_24_7" in f.columns:
        f = f[f["access_24_7"]]
    if start_date and end_date:
        ds = ensure_date_series(f)
        if ds.notna().any():
            f = f[ds.between(pd.to_datetime(start_date), pd.to_datetime(end_date))]
    if p_range and "puissance_kw" in f.columns:
        f = f[(f["puissance_kw"] >= p_range[0]) & (f["puissance_kw"] <= p_range[1])]
    return f

def kpi_row(filtered: pd.DataFrame):
    total_points = len(filtered)
    total_stations = filtered["adresse_station"].nunique() if "adresse_station" in filtered else 0
    pct_dc = (filtered["is_dc"].mean() * 100).round(1) if "is_dc" in filtered and filtered["is_dc"].notna().any() else np.nan
    pct_247 = (filtered["access_24_7"].mean() * 100).round(1) if "access_24_7" in filtered and filtered["access_24_7"].notna().any() else np.nan
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Charging points", f"{total_points:,}".replace(",", " "))
    c2.metric("Unique stations", f"{total_stations:,}".replace(",", " "))
    c3.metric("DC share (%)", "N/A" if np.isnan(pct_dc) else f"{pct_dc:.1f}%")
    c4.metric("24/7 share (%)", "N/A" if np.isnan(pct_247) else f"{pct_247:.1f}%")

def monthly_installations(df: pd.DataFrame):
    ds = ensure_date_series(df)
    ds = pd.to_datetime(ds, errors="coerce")
    s = pd.Series(1, index=ds.dropna().index)
    grp = s.groupby(ds.dropna().dt.to_period("M")).sum()

    if grp.empty:
        return pd.DataFrame({"month": [], "installations": []})

    # Force start at Jan 2020
    start = pd.Period("2021-01", freq="M")
    end = grp.index.max()
    idx = pd.period_range(start, end, freq="M")

    grp = grp.reindex(idx, fill_value=0)

    out = grp.rename("installations").to_timestamp().reset_index().rename(columns={"index": "month"})
    return out


def top_departments(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    if "departement" not in df.columns or df.empty:
        return pd.DataFrame({"departement": [], "nb": []})
    res = (
        df.groupby("departement", dropna=True)
          .size()
          .reset_index(name="nb")
          .sort_values("nb", ascending=False)
          .head(n)
    )
    return res

def ac_dc_mix(df: pd.DataFrame) -> pd.DataFrame:
    if "is_dc" not in df.columns or df["is_dc"].notna().sum() == 0:
        return pd.DataFrame({"type": [], "nb": []})
    mix = df["is_dc"].map({True: "DC (fast)", False: "AC"}).value_counts(dropna=False).reset_index()
    mix.columns = ["type", "nb"]
    return mix

def render():
    st.title("Overview")
    st.caption("Source: data/processed/irve_clean.csv")
    df = load_data("data/processed/irve_clean.csv")
    filtered = sidebar_filters(df)
    st.markdown(f"**Total rows imported: `{len(df):,}`**".replace(",", " "))
    st.subheader("Key metrics")
    kpi_row(filtered)
    st.subheader("Deployments per month")
    ts = monthly_installations(filtered)
    fig = px.line(ts, x="month", y="installations", markers=True, labels={"month": "Month", "installations": "Installations"}, title="Monthly installations (filtered view)")
    fig.update_layout(xaxis=dict(tickformat="%Y-%m"))
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Top departments by number of stations")
    top_depts = top_departments(filtered, n=15)
    fig2 = px.bar(top_depts, x="departement", y="nb", labels={"departement": "Department", "nb": "Stations"}, title="Top departments for selected departements")
    st.plotly_chart(fig2, use_container_width=True)
    st.subheader("AC vs DC mix")
    mix = ac_dc_mix(filtered)

    fig3 = px.pie(mix, names="type", values="nb", hole=0.55, title="AC vs DC")
    st.plotly_chart(fig3, use_container_width=True)
