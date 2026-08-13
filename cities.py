"""Gazetteer villes -> (lat, lon) réelles pour les théâtres DCS.

Les cartes DCS sont géo-référencées : une ville réelle se convertit en position
carte via coord.LLtoLO(lat, lon) côté mission. Liste curée et extensible.
"""
import re

CITIES = {
    # --- Syrie / Levant ---
    "damascus": (33.51, 36.29), "damas": (33.51, 36.29),
    "beirut": (33.89, 35.50), "beyrouth": (33.89, 35.50),
    "aleppo": (36.20, 37.16), "alep": (36.20, 37.16),
    "homs": (34.73, 36.71), "hama": (35.13, 36.75),
    "latakia": (35.53, 35.79), "lattaquie": (35.53, 35.79),
    "tartus": (34.89, 35.89), "palmyra": (34.56, 38.28), "palmyre": (34.56, 38.28),
    "deir ez-zor": (35.34, 40.14), "tripoli": (34.44, 35.84),
    "amman": (31.95, 35.93), "haifa": (32.79, 34.99), "haifa": (32.79, 34.99),
    "tel aviv": (32.08, 34.78), "jerusalem": (31.78, 35.22),
    "nicosia": (35.17, 33.36), "nicosie": (35.17, 33.36),
    "adana": (37.00, 35.32), "damas": (33.51, 36.29),
    # --- Golfe Persique ---
    "dubai": (25.20, 55.27), "dubai": (25.20, 55.27),
    "abu dhabi": (24.47, 54.37), "tehran": (35.69, 51.39), "teheran": (35.69, 51.39),
    "bandar abbas": (27.18, 56.28), "shiraz": (29.59, 52.58),
    "doha": (25.29, 51.53), "muscat": (23.59, 58.41), "mascate": (23.59, 58.41),
    "al ain": (24.19, 55.76), "sharjah": (25.35, 55.39),
    "bushehr": (28.92, 50.84), "kish": (26.55, 53.98), "chabahar": (25.29, 60.64),
    # --- Caucase ---
    "tbilisi": (41.72, 44.78), "tbilissi": (41.72, 44.78),
    "sochi": (43.60, 39.73), "batumi": (41.64, 41.64),
    "sukhumi": (43.01, 41.02), "kutaisi": (42.27, 42.70),
    "krasnodar": (45.04, 38.98), "novorossiysk": (44.72, 37.77),
    "anapa": (44.89, 37.32), "vladikavkaz": (43.02, 44.68),
    "senaki": (42.27, 42.06), "poti": (42.15, 41.67), "gudauta": (43.10, 40.58),
    # --- Nevada ---
    "las vegas": (36.17, -115.14), "vegas": (36.17, -115.14),
    "nellis": (36.24, -115.03), "tonopah": (38.07, -117.23),
    "beatty": (36.91, -116.76), "pahrump": (36.21, -115.98),
    # --- Sinaï ---
    "cairo": (30.04, 31.24), "le caire": (30.04, 31.24),
    "suez": (29.97, 32.55), "port said": (31.26, 32.30),
    "ismailia": (30.60, 32.27), "sharm el-sheikh": (27.92, 34.33),
    "hurghada": (27.26, 33.81), "el arish": (31.13, 33.80),
    "eilat": (29.56, 34.95), "aqaba": (29.53, 35.01), "gaza": (31.50, 34.47),
    # --- Irak ---
    "baghdad": (33.31, 44.36), "bagdad": (33.31, 44.36),
    "basra": (30.51, 47.78), "mosul": (36.34, 43.13), "mossoul": (36.34, 43.13),
    "erbil": (36.19, 44.01), "kirkuk": (35.47, 44.39), "fallujah": (33.35, 43.78),
    # --- Afghanistan ---
    "kabul": (34.55, 69.21), "kaboul": (34.55, 69.21),
    "kandahar": (31.61, 65.71), "herat": (34.35, 62.20),
    "bagram": (34.95, 69.26), "mazar": (36.71, 67.11), "jalalabad": (34.43, 70.45),
    # --- Kola ---
    "murmansk": (68.97, 33.09), "kirkenes": (69.73, 30.05),
    "rovaniemi": (66.50, 25.73), "bodo": (67.28, 14.40),
    # --- Normandie ---
    "caen": (49.18, -0.37), "le havre": (49.49, 0.11),
    "cherbourg": (49.63, -1.62), "rouen": (49.44, 1.10), "paris": (48.85, 2.35),
    # --- Mariannes ---
    "guam": (13.47, 144.75), "saipan": (15.18, 145.75), "tinian": (14.97, 145.62),
    # --- Atlantique Sud ---
    "punta arenas": (-53.16, -70.92), "ushuaia": (-54.80, -68.30),
    "rio grande": (-53.78, -67.70), "stanley": (-51.69, -57.85),
}


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


def resolve(name):
    """Renvoie (lat, lon) pour un nom de ville, sinon None. Match exact puis partiel."""
    n = _norm(name)
    if not n:
        return None
    if n in CITIES:
        return CITIES[n]
    for k, v in CITIES.items():
        if n in k or k in n:
            return v
    return None
