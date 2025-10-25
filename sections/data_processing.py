import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils.cleaning import clean_irve, add_departement_from_cp_simple
from utils.geo import extract_code_postal


def render():
    st.title("Data Processing and Preparation")
    st.markdown("---")

    st.subheader("1. Loading the raw dataset")
    st.write("""
    The dataset comes from the **IRVE Etalab Schema** (version 2.3.1 – October 2025).  
    It contains more than 170,000 public charging points with over 50 variables 
    (identifiers, operators, location, power, accessibility, dates, etc.).
    """)

    df_raw = pd.read_csv("data/irve.csv", low_memory=False)
    st.write("Raw dataset preview:", df_raw.head(10))
    st.info(f"Raw dataset dimensions: {df_raw.shape[0]:,} rows × {df_raw.shape[1]} columns")

    st.write("**Data type check**")
    st.write("""
        Before cleaning, it is important to verify that we avoid issues such as:
        - dates stored as strings
        - numerical columns stored as text
        """)

    dtypes_df = pd.DataFrame(df_raw.dtypes, columns=["Type"])
    dtypes_df["Type"] = dtypes_df["Type"].astype(str)
    st.dataframe(dtypes_df)

    st.write("We do not want date columns to be in object format. Therefore, we convert them:")

    date_cols = ["date_maj", "date_mise_en_service"]
    for col in date_cols:
        if col in df_raw.columns:
            before_type = df_raw[col].dtype
            df_raw[col] = pd.to_datetime(df_raw[col], errors="coerce")
            after_type = df_raw[col].dtype
            st.write(f"`{col}` converted: {before_type} → {after_type}")
        else:
            st.warning(f"Column `{col}` not found in dataset.")

    st.write("Preview after conversion:")
    st.dataframe(df_raw[date_cols].head(5))

    st.write("Now that date formatting is fixed, we can continue.<br>")

    st.subheader("2. Extracting postal codes from address")
    st.write("We now extract the postal code from the provided address.")
    st.write("Many rows are missing postal codes, but most addresses contain it. So we extract it:")

    df_raw["code_postal"] = df_raw["adresse_station"].apply(extract_code_postal)
    st.write("Preview with postal code:", df_raw[["adresse_station", "code_postal"]].head(100))

    st.write("For the upcoming analysis, we add a 'departement' column that will be useful for grouping stations.")
    df_raw = add_departement_from_cp_simple(df_raw, cp_col="code_postal")
    st.write("Preview CP → département:", df_raw[["code_postal", "departement"]].head(10))

    st.subheader("3. Cleaning and enrichment")
    df_clean = clean_irve(df_raw)
    st.success("Cleaning complete")
    st.dataframe(df_clean.head(10))

    st.info(f"Dimensions after cleaning: {df_clean.shape[0]:,} rows × {df_clean.shape[1]} columns")

    nb_non_247 = df_clean.loc[~df_clean["access_24_7"], "access_24_7"].count()
    total = len(df_clean)
    st.write(f"Number of **non-24/7** stations: {nb_non_247:,} / {total:,} "
             f"({nb_non_247 / total:.1%}) **so we cannot ignore them.**")

    st.subheader("4. Data quality: missing values")
    na_counts = df_clean.isna().sum().rename("nb_nan")
    na_pct = (df_clean.isna().mean() * 100).round(1).rename("%_nan")
    na_table = (
        pd.concat([na_counts, na_pct], axis=1)
        .sort_values("nb_nan", ascending=False)
    )

    st.write("Missing values table (sorted):")
    st.dataframe(na_table)

    top15 = na_table.head(15).sort_values("%_nan", ascending=True)
    st.write("Top 15 most incomplete columns (% of NaN):")
    st.bar_chart(top15["%_nan"])

    nb_cols_full = int((na_counts == 0).sum())
    nb_cols_any_nan = int((na_counts > 0).sum())
    st.info(
        f"{nb_cols_full} columns without missing values — "
        f"{nb_cols_any_nan} columns contain at least one missing value."
    )

    st.subheader("5. Removing rows without postal code")
    nb_avant = len(df_clean)
    df_clean = df_clean.dropna(subset=["code_postal"])
    nb_apres = len(df_clean)
    nb_suppr = nb_avant - nb_apres

    st.write(
        f"Rows removed: {nb_suppr:,} ({(nb_suppr / nb_avant) * 100:.1f}% of dataset)"
    )
    st.info(f"New dataset dimensions: {df_clean.shape[0]:,} rows × {df_clean.shape[1]} columns")

    st.write("Verification: remaining missing values for 'code_postal'")
    st.write(df_clean["code_postal"].isna().sum())

    st.subheader("6. Duplicate check")
    nb_doublons = df_clean.duplicated().sum()
    st.info(f"Number of duplicate rows: {nb_doublons:,}")
    st.write("Here, duplicates represent multiple charging points at the same station. We keep them because this information is meaningful for the analysis.")

    st.subheader("Outlier removal")
    st.write("""
        We detect and visualize **inconsistent extreme values**, 
        particularly on charging power and geographic coordinates.
        """)

    if "puissance_kw" in df_clean.columns:
        st.write("### a) Power analysis")
        st.write("Before removal, here is the statistical distribution:")
        st.dataframe(df_clean["puissance_kw"].describe())

        fig, ax = plt.subplots()
        ax.hist(df_clean["puissance_kw"].dropna(), bins=50)
        ax.set_xlabel("Power (kW)")
        ax.set_ylabel("Number of charging points")
        ax.set_title("Power distribution before removing outliers")
        st.pyplot(fig)

        fig2, ax2 = plt.subplots()
        ax2.boxplot(df_clean["puissance_kw"].dropna(), vert=False)
        ax2.set_xlabel("Power (kW)")
        ax2.set_title("Power boxplot — extreme values on the right")
        st.pyplot(fig2)

        seuil_puissance = 400
        nb_outliers = (df_clean["puissance_kw"] > 400).sum()

        st.write("We set a maximum power threshold at 400 kW because the most powerful chargers deliver between 300 and 320 kW.")
        st.warning(f"{nb_outliers:,} values above 400 kW detected.")
        df_clean = df_clean[df_clean["puissance_kw"] <= 400]
        st.success("Outliers above 400 kW removed.")

    else:
        st.info("Column 'puissance_kw' not found — power outlier analysis skipped.")

    st.write("### b) Geographic coordinates check")
    st.write("We remove geographic outliers (DOM-TOM coordinates).")
    st.write("Our study focuses on mainland France due to insufficient data in overseas territories.")

    if {"latitude", "longitude"}.issubset(df_clean.columns):
        mask_geo = (
                df_clean["latitude"].between(-22, 52, inclusive="both") &
                df_clean["longitude"].between(-63, 55, inclusive="both")
        )
        nb_geo_out = (~mask_geo).sum()

        st.write(f"Total geographic points: {len(df_clean):,}")
        st.write(f"Outlier coordinates detected: {nb_geo_out:,}")

        st.write("Map of charging points before removing geographic outliers")
        st.map(
            df_clean[["latitude", "longitude"]].dropna().sample(min(5000, len(df_clean))),
            size=3,
            color="#3388ff"
        )

        import pydeck as pdk

        valid_points = df_clean.loc[mask_geo, ["latitude", "longitude"]].dropna()
        invalid_points = df_clean.loc[~mask_geo, ["latitude", "longitude"]].dropna()

        layer_valid = pdk.Layer(
            "ScatterplotLayer",
            data=valid_points,
            get_position='[longitude, latitude]',
            get_fill_color='[50, 150, 255, 160]',
            get_radius=100,
        )
        layer_invalid = pdk.Layer(
            "ScatterplotLayer",
            data=invalid_points,
            get_position='[longitude, latitude]',
            get_fill_color='[255, 0, 0, 200]',
            get_radius=150,
        )

        view_state = pdk.ViewState(
            latitude=46.6,
            longitude=2.4,
            zoom=4.5,
            pitch=0,
        )

        st.pydeck_chart(pdk.Deck(layers=[layer_valid, layer_invalid], initial_view_state=view_state))

        df_clean = df_clean[mask_geo]
        st.success("Rows with geographic outliers removed.")
    else:
        st.info("Latitude/longitude columns not found.")

    st.success("Processing completed")
    st.info(f"Final dataset dimensions: {df_clean.shape[0]:,} rows × {df_clean.shape[1]} columns")

    st.write("Final dataset preview:", df_clean.head(10))

    st.subheader("8. Saving the cleaned dataset")

    import os
    save_dir = "data/processed"
    os.makedirs(save_dir, exist_ok=True)

    csv_path = os.path.join(save_dir, "irve_clean.csv")
    parquet_path = os.path.join(save_dir, "irve_clean.parquet")

    try:
        df_clean.to_csv(csv_path, index=False, encoding="utf-8")
        st.success("Data saved in CSV format")
        df_clean.to_parquet(parquet_path, index=False)
        csv_size = os.path.getsize(csv_path) / 1e6
        parquet_size = os.path.getsize(parquet_path) / 1e6
        st.info(f"CSV file size: {csv_size:.1f} MB")

    except Exception as e:
        st.error(f"Save error: {e}")

    st.write("The dataset is now ready to be used in the Overview and Deep Dive sections.")
