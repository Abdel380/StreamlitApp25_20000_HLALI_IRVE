import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    date_cols = ["date_maj", "date_mise_en_service"]
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    bool_cols = ["is_dc", "access_24_7", "est_publique", "reservation"]
    for c in bool_cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().str.lower().isin(["1", "true", "vrai", "oui", "yes"])
    num_cols = ["puissance_kw", "puissance_nominale", "latitude", "longitude", "code_postal"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["categorie_puissance", "nom_operateur", "departement"]:
        if c in df.columns and df[c].dtype == object:
            df[c] = df[c].astype("category")
    return df

@st.cache_data(show_spinner=False)
def load_dep_geojson():
    import requests
    url = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"
    return requests.get(url, timeout=10).json()

def _apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")
    depts = sorted(df["departement"].dropna().unique().tolist()) if "departement" in df else []
    sel_depts = st.sidebar.multiselect("Departments", depts, default=[])
    ops = sorted(df["nom_operateur"].dropna().unique().tolist()) if "nom_operateur" in df else []
    default_ops = ops if len(ops) <= 15 else ops[:15]
    sel_ops = st.sidebar.multiselect("Operators", ops, default=[])
    dc_choice = st.sidebar.radio("Current type", ["All", "DC", "AC"], index=0, horizontal=True)
    only_247 = st.sidebar.checkbox("Only 24/7 access", value=False)
    start_date = end_date = None
    if "date_mise_en_service" in df.columns and df["date_mise_en_service"].notna().any():
        min_date = pd.to_datetime(df["date_mise_en_service"]).min()
        max_date = pd.to_datetime(df["date_mise_en_service"]).max()
        start_date, end_date = st.sidebar.date_input(
            "Period (commissioning)",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )
    p_range = None
    if "puissance_kw" in df.columns and df["puissance_kw"].notna().any():
        pmin = float(np.nanmin(df["puissance_kw"]))
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
    if start_date and end_date and "date_mise_en_service" in f.columns:
        f = f[f["date_mise_en_service"].between(pd.to_datetime(start_date), pd.to_datetime(end_date))]
    if p_range and "puissance_kw" in f.columns:
        f = f[(f["puissance_kw"] >= p_range[0]) & (f["puissance_kw"] <= p_range[1])]
    return f

def _kpis(filtered: pd.DataFrame):
    nb_prises = len(filtered)
    nb_stations = filtered["adresse_station"].nunique() if "adresse_station" in filtered else 0
    densite = round(nb_prises / nb_stations, 1) if nb_stations > 0 else 0
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Charging points (sockets)", f"{nb_prises:,}".replace(",", " "))
    with c2:
        st.metric("Unique stations", f"{nb_stations:,}".replace(",", " "))
    with c3:
        st.metric("Sockets per station (avg.)", densite)
    with c4:
        val = filtered["puissance_kw"].mean() if "puissance_kw" in filtered else np.nan
        st.metric("Average power (kW)", f"{val:,.1f}".replace(",", " "))

def render():
    st.title("IRVE Deep Dives ")
    df = load_data("data/processed/irve_clean.csv")
    st.markdown(f"**Total rows imported: `{len(df):,}`**".replace(',', ' '))
    filtered = _apply_filters(df)
    st.subheader("Quick benchmarks (based on filters)")
    _kpis(filtered)
    st.subheader("Where are the stations?")
    if not filtered.empty and "departement" in filtered.columns:
        top_depts = (
            filtered.groupby("departement", dropna=True).size().reset_index(name="nb")
            .sort_values("nb", ascending=False).head(20)
        )
        top_depts = top_depts.sort_values("nb", ascending=True)

        fig = px.bar(top_depts, x="departement", y="nb",
                     labels={"departement": "Department", "nb": "Stations"},
                     title="Top departments by number of stations (filtered view)")
        st.plotly_chart(fig, use_container_width=True)
        st.write("When looking at the study across all departments, a small number of them account for a large proportion of charging stations, mainly around densely populated urban areas. Among these departments are 75 (Paris), 59, 13 and 77.")
        st.write("This suggests that charging availability is still uneven, and expanding in mid-tier regions would improve national coverage and reduce geographic inequality.")
    else:
        st.info("No data to display. Adjust filters to see the distribution by department.")

    st.subheader("Intensity by area (choropleth map)")
    st.caption("The redder it is, the more stations the department has (in the filtered view).")
    if "departement" in filtered.columns and not filtered.empty:
        dep_counts = (filtered.dropna(subset=["departement"])
                      .groupby("departement").size()
                      .reset_index(name="nb"))
        if dep_counts.empty:
            st.info("No department left after filtering.")
        else:
            def norm_code(x):
                s = str(x).strip().upper()
                if s in {"2A", "2B"}:
                    return s
                return s.zfill(2) if s.isdigit() and len(s) <= 2 else s
            dep_counts["code"] = dep_counts["departement"].map(norm_code)
            geojson = load_dep_geojson()
            fig = px.choropleth_mapbox(
                dep_counts,
                geojson=geojson,
                locations="code",
                featureidkey="properties.code",
                color="nb",
                color_continuous_scale="Reds",
                mapbox_style="open-street-map",
                zoom=4.6, center={"lat": 46.6, "lon": 2.2},
                opacity=0.7,
                labels={"nb": "Stations"},
                title="Station density by department (filtered view)"
            )
            fig.update_layout(margin=dict(l=0, r=0, t=60, b=0))
            fig.update_traces(hovertemplate="<b>%{location}</b><br>Stations: %{z}<extra></extra>")
            st.plotly_chart(fig, use_container_width=True)
            st.write("Once again, we can see the geographical phenomenon known as the ‘diagonale du vide’ (empty diagonal) at work here, but this time reversed. From the north-west to the south-east, there is no area with a high density of charging stations.")
            st.write("To ensure equal access, investments should prioritize low-density regions rather than reinforcing areas that are already well covered.")
    else:
        st.info("Missing 'departement' column — choropleth cannot be displayed.")
    st.header("Capacity & Accessibility")
    st.markdown(
        "Having a charger is not enough: the experience depends on **charging speed** (power) "
        "and **availability** (24/7). This section assesses the quality of use of the filtered network."
    )
    st.subheader("2.1 - Network speed (power, kW)")
    if "puissance_kw" in filtered.columns and filtered["puissance_kw"].notna().any():
        df_power = filtered.dropna(subset=["puissance_kw"]).copy()
        if "categorie_puissance" not in df_power.columns:
            bins = [-0.1, 7.5, 22, 50, 150, 10000]
            labels = ["≤7.4 kW (slow)", "7.4–22 kW (AC)", "24–49 kW (fast)", "≥50–150 kW (DC)", ">150 kW (HPC)"]
            df_power["categorie_puissance"] = pd.cut(df_power["puissance_kw"], bins=bins, labels=labels)
        fig_hist = px.histogram(
            df_power,
            x="puissance_kw",
            nbins=40,
            labels={"puissance_kw": "Power (kW)"},
            title="Distribution of charging point power"
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        st.write("Most chargers deliver low or medium power, while high-power fast chargers remain a minority.")
        st.write("This slows down the adoption of long-distance electric vehicles. It is therefore important to develop fast charging (DC) to support mobility in rural areas, on motorways and interurban roads.")
    else:
        st.info("Power data unavailable in the filtered view.")
    st.subheader("2.2 - AC / DC mix")
    if "is_dc" in filtered.columns and filtered["is_dc"].notna().any():
        mix_dc = (
            filtered["is_dc"].map({True: "DC (fast)", False: "AC"}).value_counts(dropna=False).reset_index()
        )
        mix_dc.columns = ["type", "nb"]
        fig_mix = px.pie(
            mix_dc,
            names="type",
            values="nb",
            hole=0.5,
            title="AC vs DC breakdown"
        )
        st.plotly_chart(fig_mix, use_container_width=True)
        st.write("Without a stronger fast-charging backbone, electric vehicule users face longer charging times, especially during travel, which continues to limit EV usage confidence.")
    else:
        st.info("Cannot determine AC/DC (missing/empty `is_dc` column).")


    st.subheader("2.3 - Accessibility (24/7)")
    acc = (
        filtered["access_24_7"].map({True: "24/7", False: "Restricted"}).value_counts(dropna=False).reset_index()
    )
    acc.columns = ["access", "nb"]
    fig_247 = px.pie(
        acc,
        names="access",
        values="nb",
        hole=0.5,
        title="Share of chargers accessible 24/7"
    )
    st.plotly_chart(fig_247, use_container_width=True)
    st.write("A significant portion of stations are not accessible 24/7, creating time-based service gaps for drivers.")


    st.subheader("2.4 - Territorial prioritization (DC share)")
    st.markdown(
        "Goal: identify territories under-equipped with fast charging (DC). "
        "We compute the **% of DC by department** to prioritize investments."
    )
    if {"departement", "is_dc"}.issubset(filtered.columns) and filtered[["departement", "is_dc"]].notna().any().any():
        dep_mix = (
            filtered.dropna(subset=["departement"])
                    .groupby("departement", dropna=True)
                    .agg(nb=("is_dc", "size"), dc=("is_dc", "sum"))
                    .reset_index()
        )
        if not dep_mix.empty:
            dep_mix["pct_dc"] = (dep_mix["dc"] / dep_mix["nb"] * 100).round(1)
            seuil = 20
            dep_mix_f = dep_mix[dep_mix["nb"] >= seuil].copy()
            if dep_mix_f.empty:
                dep_mix_f = dep_mix.copy()
            dep_mix_f = dep_mix_f.sort_values("pct_dc", ascending=False).head(20)
            fig_pct = px.bar(
                dep_mix_f,
                x="departement",
                y="pct_dc",
                labels={"departement": "Department", "pct_dc": "% DC"},
                title="Top departments by DC share (≥50 kW) — filtered view"
            )
            st.plotly_chart(fig_pct, use_container_width=True)
            best_row = dep_mix_f.iloc[0]
            worst_row = dep_mix_f.iloc[-1]
            st.caption(
                f"Reading: **{best_row['departement']}** shows the highest DC share ({best_row['pct_dc']}%). "
                f"Conversely, **{worst_row['departement']}** is at the bottom ({worst_row['pct_dc']}%)."
            )
            st.write("DC infrastructure deployment is highly uneven: some territories are well ahead while others lag behind.")
            st.write("Targeting the lowest-performing departments first would maximize impact and accelerate network reliability at the national level.")
        else:
            st.info("No aggregation possible by department.")
    else:
        st.info("Required columns are missing (`departement`, `is_dc`).")


    st.header("Territorial accessibility per inhabitant")
    st.markdown(
        "To measure real accessibility, we observe how many inhabitants share a charger. "
        "The higher the number, the more under-equipped the area."
    )
    POP_BY_DEP = {
        "01": 656000, "02": 526000, "03": 337000, "04": 166000, "05": 146000, "06": 1084000, "07": 334000,
        "08": 265000, "09": 158000, "10": 297000, "11": 380000, "12": 279000, "13": 2043000, "14": 694000,
        "15": 143000, "16": 352000, "17": 662000, "18": 307000, "19": 227000, "2A": 177000, "2B": 176000,
        "21": 528000, "22": 605000, "23": 118000, "24": 414000, "25": 541000, "26": 524000, "27": 600000,
        "28": 446000, "29": 954000, "30": 783000, "31": 1506000, "32": 192000, "33": 1657000, "34": 1187000,
        "35": 1120000, "36": 220000, "37": 620000, "38": 1298000, "39": 259000, "40": 425000, "41": 327000,
        "42": 765000, "43": 227000, "44": 1496000, "45": 683000, "46": 176000, "47": 330000, "48": 76000,
        "49": 834000, "50": 499000, "51": 571000, "52": 170000, "53": 318000, "54": 730000, "55": 180000,
        "56": 772000, "57": 1054000, "58": 195000, "59": 2607000, "60": 830000, "61": 278000, "62": 1453000,
        "63": 660000, "64": 683000, "65": 228000, "66": 486000, "67": 1160000, "68": 799000, "69": 1867000,
        "70": 235000, "71": 551000, "72": 567000, "73": 450000, "74": 844000, "75": 2125000, "76": 1260000,
        "77": 1469000, "78": 1460000, "79": 381000, "80": 571000, "81": 392000, "82": 262000, "83": 1123000,
        "84": 573000, "85": 700000, "86": 444000, "87": 370000, "88": 364000, "89": 331000, "90": 141000,
        "91": 1328000, "92": 1615000, "93": 1662000, "94": 1399000, "95": 1249000,
        "971": 383000, "972": 361000, "973": 296000, "974": 865000, "976": 310000
    }
    if not filtered.empty and "departement" in filtered.columns:
        dep_counts = filtered.groupby("departement").size().reset_index(name="nb_bornes")
        dep_counts["code"] = dep_counts["departement"].astype(str).str.zfill(2)
        dep_counts.loc[dep_counts["departement"].astype(str).str.upper() == "2A", "code"] = "2A"
        dep_counts.loc[dep_counts["departement"].astype(str).str.upper() == "2B", "code"] = "2B"
        dep_counts["population"] = dep_counts["code"].map(POP_BY_DEP)
        dep_counts = dep_counts.dropna(subset=["population"])
        dep_counts["people_per_charger"] = (dep_counts["population"] / dep_counts["nb_bornes"]).round(0)
        dep_sorted = dep_counts.sort_values("people_per_charger", ascending=False)
        fig_hab = px.bar(
            dep_sorted,
            x="departement",
            y="people_per_charger",
            labels={"departement": "Department", "people_per_charger": "People per charger"},
            title="People per charger — from least to best equipped territory",
        )
        st.plotly_chart(fig_hab, use_container_width=True)
        worst = dep_sorted.iloc[0]
        best = dep_sorted.iloc[-1]
        st.markdown(
            f"**Note:** in **{worst['departement']}**, there is **1 charger for {worst['people_per_charger']:.0f} people**, "
            f"while **{best['departement']}** performs much better (**1 charger for {best['people_per_charger']:.0f} people**)."
        )

    else:
        st.info("Unable to compute accessibility per inhabitant.")
    st.header("Top operators of the IRVE network")
    st.markdown(
        "Who is actually building the network? This ranking highlights the most active operators. "
        "They are strategic partners in tackling charging deserts."
    )
    if "nom_operateur" in filtered.columns and not filtered.empty:
        op_counts = (
            filtered.groupby("nom_operateur")
                    .size()
                    .reset_index(name="nb_bornes")
                    .sort_values("nb_bornes", ascending=False)
                    .head(10)
        )
        fig_ops = px.bar(
            op_counts,
            x="nb_bornes",
            y="nom_operateur",
            orientation="h",
            labels={"nb_bornes": "Number of chargers", "nom_operateur": "Operator"},
            title="Top 10 operators by number of chargers"
        )
        fig_ops.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_ops, use_container_width=True)
        top_name = op_counts.iloc[0]["nom_operateur"]
        top_value = op_counts.iloc[0]["nb_bornes"]
        st.markdown(
            f"**Key takeaway:** operator **{top_name}** ranks first with **{top_value} chargers** "
            "in the filtered area, illustrating the strong market concentration."
        )
        st.write("Public–private collaboration can accelerate deployment, but diversification is needed to reduce dependency.")
    else:
        st.info("No operator data available in the filtered view.")
