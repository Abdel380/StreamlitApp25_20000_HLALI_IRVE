# utils/geo.py
import re
import pandas as pd

def extract_code_postal(adresse):
    """
    Extrait un code postal à 5 chiffres depuis une chaîne d'adresse.
    Retourne None si aucun code postal n'est trouvé.
    """
    if pd.isna(adresse):
        return None
    match = re.search(r"\b(\d{5})\b", str(adresse))
    return match.group(1) if match else None
