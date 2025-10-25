# utils/cleaning.py
import pandas as pd
import numpy as np
import re

def add_departement_from_cp_simple(df: pd.DataFrame, cp_col: str = "code_postal") -> pd.DataFrame:
    """
    Ajoute une colonne 'departement' = deux premiers chiffres du code postal.
    (Version simple, sans gestion Corse/DOM.)
    """
    if cp_col in df.columns:
        df["departement"] = df[cp_col].astype(str).str.extract(r"^(\d{2})", expand=False)
    else:
        df["departement"] = None
    return df

def extract_code_postal(adresse):
    """Retourne le 1er code postal (5 chiffres) trouvé dans une adresse, sinon None."""
    if pd.isna(adresse):
        return None
    m = re.search(r"\b(\d{5})\b", str(adresse))
    return m.group(1) if m else None


def clean_irve(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()

    # --- 1) Colonnes utiles (garde ce qui existe réellement)
    cols = [
        # IDs & libellé
        "id_station", "id_pdc", "nom_station",

        # Adresse & géo
        "adresse_station", "code_postal", "nom_commune",
        "code_departement", "nom_departement", "code_region", "nom_region",
        "latitude", "longitude",
        # Consolidated (NE PAS SUPPRIMER)
        "consolidated_longitude", "consolidated_latitude", "consolidated_lagitude",

        # Accessibilité
        "accessibilite", "conditions_acces", "horaires", "reservation", "modalites_paiement",

        # Statut / fiabilité
        "etat_pdc", "statut_pdc", "date_maj", "date_mise_en_service",

        # Puissance / connecteurs
        "puissance_nominale", "type_prise", "connecteur", "format_recharge", "type_charge",
        "nb_points_charge",

        # Exploitant
        "operateur", "nom_operateur", "enseigne", "reseau", "proprietaire",

        # Métadonnées
        "source", "last_update",

        # À supprimer plus bas si présent
        "code_insee_commune",
        "departement",
    ]
    present = [c for c in cols if c in df.columns]
    df = df[present].copy()

    # --- 2) Latitude/Longitude depuis les "consolidated_*" (ultra simple)
    # Priorité aux colonnes consolidated si présentes, sans supprimer les colonnes d'origine.
    if "consolidated_longitude" in df.columns:
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce") if "longitude" in df.columns else np.nan
        df["longitude"] = df["longitude"].fillna(pd.to_numeric(df["consolidated_longitude"], errors="coerce"))

    # Certains fichiers ont "consolidated_latitude" (bonne orthographe)
    if "consolidated_latitude" in df.columns:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce") if "latitude" in df.columns else np.nan
        df["latitude"] = df["latitude"].fillna(pd.to_numeric(df["consolidated_latitude"], errors="coerce"))

    # D'autres ont "consolidated_lagitude" (typo fréquente)
    if "consolidated_lagitude" in df.columns:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce") if "latitude" in df.columns else np.nan
        df["latitude"] = df["latitude"].fillna(pd.to_numeric(df["consolidated_lagitude"], errors="coerce"))

    # --- 3) Puissance numérique & catégories (simple)
    if "puissance_nominale" in df.columns:
        df["puissance_kw"] = pd.to_numeric(df["puissance_nominale"], errors="coerce").clip(lower=0)
        def _bin(x):
            if pd.isna(x): return "inconnu"
            if x <= 7: return "AC_lente"
            if x <= 22: return "AC_standard"
            if x <= 49: return "DC_moyenne"
            if x <= 149: return "DC_rapide"
            return "DC_ultra"
        df["categorie_puissance"] = df["puissance_kw"].apply(_bin)

    # --- 4) AC/DC (règle simple)
    if "connecteur" in df.columns:
        df["is_dc"] = df["connecteur"].str.contains("DC|CCS|Combo|CHAdeMO", case=False, na=False)
    elif "puissance_kw" in df.columns:
        df["is_dc"] = df["puissance_kw"].ge(24)

    # --- 5) Accessibilité 24/7 (règle simple sur le texte des horaires)
    if "horaires" in df.columns:
        s = df["horaires"].astype(str).str.lower()
        df["access_24_7"] = (
            s.str.contains("24/7") | s.str.contains("24h") |
            s.str.contains("24 h") | s.str.contains("24 heures")
        )
    else:
        df["access_24_7"] = False

    # --- 6) Public vs privé (heuristique minimaliste)
    # --- 6) Public vs privé (heuristique minimaliste)  <<<<<< FIX ICI
    a = df["accessibilite"].astype(str) if "accessibilite" in df.columns else pd.Series("", index=df.index)
    c = df["conditions_acces"].astype(str) if "conditions_acces" in df.columns else pd.Series("", index=df.index)
    txt = (a + " " + c).str.lower()
    df["est_publique"] = txt.str.contains("public|libre accès|libre acces", regex=True)

    # --- 7) Statut normalisé (simple mapping)
    statut_src = "etat_pdc" if "etat_pdc" in df.columns else ("statut_pdc" if "statut_pdc" in df.columns else None)
    if statut_src:
        s = df[statut_src].astype(str).str.lower()
        df["statut_normalise"] = np.select(
            [
                s.str.contains("en service|disponible|opération|operation"),
                s.str.contains("hors service|panne|indisponible"),
                s.str.contains("maintenance"),
            ],
            ["en_service", "hors_service", "maintenance"],
            default="inconnu"
        )

    # --- 8) Supprimer la colonne INUTILE demandée
    if "code_insee_commune" in df.columns:
        df = df.drop(columns=["code_insee_commune"])

    # --- 9) Réordonner quelques colonnes clés devant (optionnel)
    front = [c for c in [
        "id_station", "id_pdc", "nom_station",
        "adresse_station", "code_postal", "nom_commune",
        "code_departement", "nom_departement", "code_region", "nom_region",
        "latitude", "longitude",
        "puissance_kw", "categorie_puissance", "is_dc",
        "access_24_7", "est_publique", "statut_normalise",
        "operateur", "enseigne", "reseau",
        "date_maj", "date_mise_en_service",
    ] if c in df.columns]
    df = df[front + [c for c in df.columns if c not in front]]

    if "consolidated_latitude" in df.columns:
        df = df.drop(columns=["consolidated_latitude"])
    if "consolidated_longitude" in df.columns:
        df = df.drop(columns=["consolidated_longitude"])

    return df
