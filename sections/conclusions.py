import streamlit as st

def render():
    st.markdown("### Conclusion")
    st.write("Accessibility is improving across the country over time, but remains uneven. Furthermore, reliability for long distances remains limited. Since 2021, deployments have accelerated according to our data, but the network remains concentrated around major cities. Fast charging (DC) and 24/7 availability are not keeping pace everywhere, resulting in disparities between regions. In order to reduce these disparities by 2026, investments should prioritise departments with (i) a high number of inhabitants per charger, (ii) a low share of DC charging, and (iii) a low density of stations.")

    st.markdown("### Project Limitations")

    st.write("""
    Although the dataset provides solid insights into national trends, several limitations must be acknowledged:

    - **Incomplete coverage of all charging operators and networks**: the analysis relies on the Etalab IRVE dataset,
      which does not include 100% of private or semi-private charging networks. Some operators and commercial chargers 
      may therefore be under-represented.

    - **Sparse or unreliable data in overseas territories (DOM-TOM)**: very few stations are declared, and metadata 
      quality is significantly lower. For this reason, our territorial conclusions mainly apply to mainland France.

    - **Limited temporal depth before 2021**: earlier data is incomplete or inconsistent, preventing a robust 
      long-term trend analysis.

    - **AC/DC availability and 24/7 status depend on self-reported operator data**, which may introduce variability or 
      reporting bias.

    Despite these constraints, the dataset remains sufficiently rich to identify major patterns, territorial disparities,
    and clear policy priorities.
    """)

    st.markdown("### Final Takeaway")

    st.write("""
    Building more stations is no longer the only challenge. We have to improve the quality of the network. Fast charging,
    24/7 availability and territorial equity are now the key to supporting EV adoption at scale. With targeted investment
    and better data integration, France can move from a fragmented network to a reliable, nation-wide infrastructure by 2025–2026.
    """)