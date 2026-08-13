"""Multi-persona : rôles, construction de prompt, et routage par indicatif.

Un persona = { id, callsign, freq, language, voice (chemin Piper), role, enabled }.
Le pilote adresse un persona en commençant par son indicatif ("Overlord, picture").
Chaque persona répond dans SA langue avec SA voix et les outils de SON rôle.
"""
import re

import dcs_config


def _norm(s):
    """Normalise pour comparer des indicatifs (minuscules, alphanum only)."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def match_callsign(transcript, personas):
    """Renvoie le persona dont l'indicatif est reconnu dans le texte, sinon None
    (sans repli). Tolérant : compare en normalisé, indicatif le plus long d'abord."""
    t = _norm(transcript)
    if not t:
        return None
    cands = [p for p in personas if p.get("enabled", True) and p.get("callsign")]
    cands.sort(key=lambda p: len(_norm(p["callsign"])), reverse=True)
    for p in cands:
        cs = _norm(p["callsign"])
        if cs and cs in t:
            return p
    return None

ROLES = {
    "operator": {
        "label": "Opérateur / instructeur",
        "tools": ["get_telemetry", "spawn_aircraft", "spawn_ground", "spawn_ship",
                  "spawn_prefab", "spawn_static", "battlefield_mark", "order_engage",
                  "highlight_cockpit_control", "clear_cockpit_highlight"],
        "brief": ("opérateur de jeu et instructeur. Tu peux faire apparaître des "
                  "unités aériennes, au sol ET navales (chars, DCA, SAM, véhicules, "
                  "navires, porte-avions, ravitailleurs, AWACS), escortes, renforts ou "
                  "ennemis, ordonner aux alliés d'engager (order_engage). "
                  "POSITIONNEMENT : utilise le paramètre reference (player/mark/bullseye/"
                  "airbase/city/coords). Pour un lieu nommé (ville, aérodrome), utilise "
                  "reference=city/airbase avec place=<nom> — ne DEVINE JAMAIS un cap/distance. "
                  "Si tu ne peux pas situer l'endroit, demande au pilote de poser un repère F10 "
                  "(reference=mark). Tu peux aussi encadrer les commandes du "
                  "cockpit et guider les procédures (démarrage, décollage, "
                  "atterrissage) étape par étape."),
    },
    "awacs": {
        "label": "AWACS / contrôleur",
        "tools": ["get_telemetry", "battlefield_mark"],
        "brief": ("contrôleur AWACS. Tu donnes la situation tactique et aides à "
                  "localiser les unités (picture, bogey dope), façon contrôle radar."),
    },
    "wingman": {
        "label": "Ailier (coéquipier)",
        "tools": ["get_telemetry", "spawn_aircraft"],
        "brief": ("l'ailier du pilote (coéquipier dans un autre avion). Tu exécutes "
                  "les ordres du leader et réponds brièvement, façon équipier."),
    },
}


def role_label(role):
    return ROLES.get(role, ROLES["operator"])["label"]


def role_tools(role, all_tools):
    names = ROLES.get(role, ROLES["operator"])["tools"]
    return [t for t in all_tools if t["name"] in names]


def build_prompt(persona):
    lang = dcs_config.LANG_NAMES.get(persona.get("language", "fr"),
                                     persona.get("language", "fr"))
    role = ROLES.get(persona.get("role", "operator"), ROLES["operator"])
    cs = persona.get("callsign") or "Copilote"
    return (
        f"Tu es {cs}, {role['brief']}\n\n"
        f"LANGUE : tu réponds TOUJOURS en {lang}, quelle que soit la langue de la consigne.\n\n"
        "STYLE : réponses TRÈS courtes, style brevity radio militaire. Une seule "
        "phrase si possible. Pas de politesse ni de blabla. AUCUN formatage : ni "
        "markdown, ni astérisques, ni tirets, ni listes — que du texte parlé.\n\n"
        "UNITÉS aéronautiques : altitude en pieds, vitesse en nœuds, cap sur "
        "3 chiffres. Appelle get_telemetry pour l'état de vol.\n"
        f"Ton indicatif est {cs}."
    )


def route(transcript, personas, active_id):
    """Renvoie (persona, message_sans_indicatif). Route par indicatif en tête ;
    à défaut, le persona actif ; à défaut le premier activé."""
    enabled = [p for p in personas if p.get("enabled", True)]
    low = transcript.lower().lstrip(" ,:.-")
    for p in enabled:
        cs = (p.get("callsign") or "").lower().strip()
        if cs and (low.startswith(cs) or low.startswith(cs.replace("-", " "))):
            # retire l'indicatif détecté en tête
            rest = transcript.strip()[len(cs):].lstrip(" ,:.-")
            return p, (rest or transcript.strip())
    for p in enabled:
        if p.get("id") == active_id:
            return p, transcript.strip()
    return (enabled[0] if enabled else None), transcript.strip()
