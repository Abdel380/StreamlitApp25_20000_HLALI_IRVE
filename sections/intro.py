# sections/intro.py
import streamlit as st

def render():
    st.title("Charging stations in France: accessibility and prioritisation of installation areas.")

    st.subheader("Contexte")
    st.markdown("""
    The transition to electric vehicles is accelerating in France. More and more public policies are encouraging the growth of the electric vehicle market through social leasing and various other measures.
    To support this development, a dense and reliable network of charging infrastructure needs to be rolled out. However, the distribution of these charging stations is very uneven across the country, and their ‘accessibility’ is not necessarily guaranteed, which can be a challenge for users in their everyday lives.
    In this context, we will attempt to analyse the current situation of the public network (owned by private companies) of charging stations in order to identify under-equipped areas and possible areas for improvement.
    """)

    st.subheader("Problem")
    st.markdown("""
    **How are the accessibility and reliability of the public charging station network evolving in France, and in which areas should investment be prioritised to reduce disparities by 2026?**
    """)

    st.subheader("Data used")
    st.markdown("""
    - **Source :** Schéma national [IRVE – Infrastructures de Recharge pour Véhicules Électriques](https://www.data.gouv.fr/datasets/base-nationale-des-irve-infrastructures-de-recharge-pour-vehicules-electriques/)  
      (last dataframe version 2.3.1 – october 2025).  
    - **Type :**  (*Open Data*) describing each public charging point (location, power, operator, accessibility, etc.).  
    - **Frequency :** monthly update.
    - **License :** Licence Ouverte / Open Licence  
    """)

    st.subheader("Limitations of the analysis")
    st.markdown("""
    - The game only covers stations published in Etalab format: some companies, such as TotalEnergies, may have missing data.
- No regional information is provided in the raw file, and the columns related to INSEE codes, postcodes, etc. are completely empty.
- My results are descriptive and aim to identify trends.
    """)

    st.caption("Section : Introduction — Contexte, problématique, sources et limites.")