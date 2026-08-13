"""Prefabs = paquets tactiques réalistes, spawnables par la voix.

Chaque prefab a une variante 'blue' (OTAN) et 'red' (RU) choisie selon le camp.
- cat 'ground'/'ship' : liste de types d'unités (placées en petite grille).
- cat 'air' : {aircraft, count, mission} passé à spawn_aircraft.
"""

PREFABS = {
    "sam_long": {"label": "Site SAM longue portée (S-300 / Patriot)", "cat": "ground",
                 "red": ["S-300PS 64H6E sr", "S-300PS 40B6M tr", "S-300PS 54K6 cp",
                         "S-300PS 5P85C ln", "S-300PS 5P85C ln", "S-300PS 5P85C ln"],
                 "blue": ["Patriot str", "Patriot cp", "Patriot AMG", "Patriot ECS",
                          "Patriot ln", "Patriot ln", "Patriot ln"]},
    "sam_med": {"label": "Site SAM moyenne portée (Buk / Hawk)", "cat": "ground",
                "red": ["SA-11 Buk SR 9S18M1", "SA-11 Buk CC 9S470M1",
                        "SA-11 Buk LN 9A310M1", "SA-11 Buk LN 9A310M1"],
                "blue": ["Hawk sr", "Hawk tr", "Hawk pcp", "Hawk ln", "Hawk ln", "Hawk ln"]},
    "sam_short": {"label": "SAM courte portée (Tor / Avenger)", "cat": "ground",
                  "red": ["Tor 9A331", "Tor 9A331"],
                  "blue": ["M1097 Avenger", "M1097 Avenger"]},
    "shorad": {"label": "DCA courte portée (canons + IR)", "cat": "ground",
               "red": ["ZSU-23-4 Shilka", "ZSU-23-4 Shilka", "2S6 Tunguska", "Strela-10M3"],
               "blue": ["Vulcan", "Vulcan", "M6 Linebacker", "M1097 Avenger"]},
    "armor": {"label": "Colonne blindée", "cat": "ground",
              "red": ["T-90", "T-90", "T-90", "BMP-2", "BMP-2", "ZSU-23-4 Shilka"],
              "blue": ["M-1 Abrams", "M-1 Abrams", "M-1 Abrams", "M-2 Bradley",
                       "M-2 Bradley", "Vulcan"]},
    "convoy": {"label": "Convoi logistique", "cat": "ground",
               "red": ["Ural-375", "Ural-375", "Ural-375", "ZSU-23-4 Shilka"],
               "blue": ["M 818", "M 818", "M 818", "Vulcan"]},
    "infantry": {"label": "Section d'infanterie", "cat": "ground",
                 "red": ["Infantry AK", "Infantry AK", "Infantry AK", "Infantry AK", "Infantry AK"],
                 "blue": ["Soldier M4", "Soldier M4", "Soldier M4", "Soldier M4", "Soldier M4"]},
    "cap": {"label": "Patrouille de chasse (CAP x4)", "cat": "air",
            "red": {"aircraft": "Su-27", "count": 4, "mission": "cap"},
            "blue": {"aircraft": "F-16C_50", "count": 4, "mission": "cap"}},
    "strike": {"label": "Paire d'attaque au sol", "cat": "air",
               "red": {"aircraft": "Su-25", "count": 2, "mission": "cas"},
               "blue": {"aircraft": "A-10C_2", "count": 2, "mission": "cas"}},
    "carrier": {"label": "Groupe naval (porte-avions + escorte)", "cat": "ship",
                "red": ["KUZNECOW", "REZKY", "MOLNIYA"],
                "blue": ["CVN_71", "TICONDEROG", "PERRY"]},
}


import re

# Désignations/synonymes (OTAN, russe, français) -> clé de prefab.
ALIASES = {
    "sa10": "sam_long", "s300": "sam_long", "patriot": "sam_long", "longrange": "sam_long",
    "sa11": "sam_med", "buk": "sam_med", "sa6": "sam_med", "kub": "sam_med", "hawk": "sam_med",
    "sa15": "sam_short", "tor": "sam_short", "sa8": "sam_short", "osa": "sam_short", "avenger": "sam_short",
    "dca": "shorad", "aaa": "shorad", "flak": "shorad", "shilka": "shorad", "tunguska": "shorad",
    "colonneblindee": "armor", "chars": "armor", "tanks": "armor", "blindes": "armor", "char": "armor",
    "convoi": "convoy", "logistique": "convoy",
    "infanterie": "infantry", "troupes": "infantry", "soldats": "infantry",
    "patrouille": "cap", "chasse": "cap", "cap4": "cap", "chasseurs": "cap",
    "attaque": "strike", "cas": "strike",
    "porteavions": "carrier", "portavion": "carrier", "groupenaval": "carrier", "flotte": "carrier",
}


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# Index des clés de prefab normalisées (ex. "samlong" -> "sam_long").
_NORM_KEYS = {_norm(k): k for k in PREFABS}


def get(name):
    """Résout un nom de prefab de façon tolérante : clé, désignation (SA-10, S-300,
    Patriot...), français, ou correspondance partielle."""
    n = _norm(name)
    if not n:
        return None
    key = _NORM_KEYS.get(n) or ALIASES.get(n)
    if key:
        return PREFABS[key]
    for nk, k in _NORM_KEYS.items():
        if n in nk or nk in n:
            return PREFABS[k]
    for ak, k in ALIASES.items():
        if n in ak or ak in n:
            return PREFABS[k]
    return None


def units_for(prefab, side):
    """Liste de types d'unités pour le camp (ground/ship)."""
    return prefab["blue"] if side == "friendly" else prefab["red"]


def air_for(prefab, side):
    """Dict {aircraft, count, mission} pour un prefab air."""
    return prefab["blue"] if side == "friendly" else prefab["red"]


def grid_spec(unit_types, spacing=40):
    """Place les unités en petite grille : renvoie [{t, dx, dz}]."""
    spec = []
    n = len(unit_types)
    cols = max(1, int(n ** 0.5 + 0.999))
    for i, t in enumerate(unit_types):
        row, col = divmod(i, cols)
        spec.append({"t": t, "dx": col * spacing, "dz": row * spacing})
    return spec
