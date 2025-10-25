# app.py
import streamlit as st

# Import des sections
from sections import intro, data_processing, deep_dives, overview, conclusions

# Configuration globale
st.set_page_config(page_title="IRVE France — Dashboard", layout="wide")

# Barre latérale de navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Aller à la section :",
    ("Introduction", "Data Processing", "Deep Dives", "Overview", "Conclusion")
)

# Affichage conditionnel des pages
if page == "Introduction":
    intro.render()
elif page == "Data Processing":
    data_processing.render()
elif page == "Deep Dives":
    deep_dives.render()
elif page == "Overview":
    overview.render()
elif page == "Conclusion":
    conclusions.render()
# Pied de page (optionnel)
st.sidebar.markdown("---")
st.sidebar.caption("Projet Data Storytelling — H’lali • 2025")
