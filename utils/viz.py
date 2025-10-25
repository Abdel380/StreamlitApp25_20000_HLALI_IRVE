# utils/viz.py
import plotly.express as px
import streamlit as st
import pydeck as pdk
import pandas as pd

def bar_regions(df):
    if df.empty:
        st.info("Aucune donnée pour ce filtre.")
        return
    fig = px.bar(df.sort_values("points", ascending=False).head(20),
                 x="region", y="points",
                 color="pct_service",
                 labels={"points":"Points de charge","region":"Région","pct_service":"% en service"},
                 hover_data=["pct_service","pct_fast"])
    st.plotly_chart(fig, use_container_width=True)

def bar_power_dist(df):
    fig = px.bar(df, x="power_kw_bin", y="count",
                 labels={"power_kw_bin":"Puissance (kW)","count":"Nombre"})
    st.plotly_chart(fig, use_container_width=True)

def map_points(df):
    if df.empty:
        st.info("Pas de points géolocalisés à afficher.")
        return
    st.pydeck_chart(pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(latitude=float(df["lat"].mean()),
                                         longitude=float(df["lon"].mean()),
                                         zoom=5),
        layers=[
            pdk.Layer(
                "HeatmapLayer",
                data=df, get_position='[lon, lat]', aggregation='MEAN',
                get_weight='power_kw'  # chauffe sur la puissance
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=df,
                get_position='[lon, lat]',
                get_radius=200,
                pickable=True,
                opacity=0.6
            )
        ],
        tooltip={"text": "Puissance: {power_kw} kW\nStatut: {status}\nOpérateur: {operator}"}
    ))

def bar_communes(df):
    if df is None or df.empty:
        st.info("Aucune donnée disponible.")
        return
    # nom de colonne dépendant (commune ou CP)
    label_col = "consolidated_commune" if "consolidated_commune" in df.columns else (
        "consolidated_code_postal" if "consolidated_code_postal" in df.columns else None
    )
    if label_col is None:
        st.info("Pas de commune/code postal dans ce jeu.")
        return
    top = df.dropna(subset=[label_col]).sort_values("points", ascending=False).head(20)
    fig = px.bar(top, x=label_col, y="points",
                 color="pct_fast",
                 labels={label_col: "Commune / CP", "points": "Points de charge", "pct_fast": "% DC ≥50 kW"})
    st.plotly_chart(fig, use_container_width=True)

