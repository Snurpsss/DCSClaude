"""Sélection et ouverture des micros - via WASAPI pour coller à la liste Windows.

PortAudio énumère chaque micro une fois par API (MME, DirectSound, WASAPI, WDM-KS)
+ des entrées virtuelles. Windows n'affiche que les endpoints WASAPI actifs :
on filtre donc sur WASAPI. Pour l'enregistrement, WASAPI en mode partagé exige la
fréquence/canaux natifs -> on active l'auto-conversion (auto_convert=True) pour
pouvoir capter directement en 16 kHz mono.
"""
import sounddevice as sd


def _wasapi_hostapi_index():
    for i, h in enumerate(sd.query_hostapis()):
        if "WASAPI" in h["name"]:
            return i
    return None


def list_input_devices():
    """Micros actifs, filtrés WASAPI (comme la liste Windows), dédupliqués."""
    wa = _wasapi_hostapi_index()
    hostapis = sd.query_hostapis()
    devices = sd.query_devices()
    out, seen = [], set()
    for i, d in enumerate(devices):
        if d["max_input_channels"] <= 0:
            continue
        if wa is not None and d["hostapi"] != wa:
            continue
        name = d["name"]
        if "loopback" in name.lower():
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"index": i, "name": name,
                    "hostapi": hostapis[d["hostapi"]]["name"]})
    # Repli si aucune entrée WASAPI (config exotique) : tout ce qui a une entrée.
    if not out:
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                out.append({"index": i, "name": d["name"],
                            "hostapi": hostapis[d["hostapi"]]["name"]})
    return out


def resolve_input_device(name, fallback_index=None):
    """Retrouve l'index d'un micro par son nom (les index bougent si on
    branche/débranche du matériel). Repli sur l'index mémorisé, sinon défaut."""
    if name:
        for d in list_input_devices():
            if d["name"] == name:
                return d["index"]
    return fallback_index


def resolve_output_device(name):
    """Retrouve l'index d'un périphérique de SORTIE par son nom (WASAPI en priorité).
    Match exact puis sous-chaîne (ex. 'Oculus' present des deux côtés). None = défaut."""
    if not name:
        return None
    devs = sd.query_devices()
    has = sd.query_hostapis()
    cands = [(i, d) for i, d in enumerate(devs) if d["max_output_channels"] > 0]
    cands.sort(key=lambda x: 0 if "WASAPI" in has[x[1]["hostapi"]]["name"] else 1)
    for i, d in cands:
        if d["name"] == name:
            return i
    low = name.lower()
    for i, d in cands:
        n = d["name"].lower()
        if low in n or n in low:
            return i
    return None


def input_extra_settings(device):
    """Renvoie les WasapiSettings(auto_convert) si le device est WASAPI, sinon None.
    Valable pour l'entrée ET la sortie (conversion fréquence/canaux automatique)."""
    if device is None:
        return None
    try:
        d = sd.query_devices(device)
        h = sd.query_hostapis()[d["hostapi"]]
        if "WASAPI" in h["name"]:
            return sd.WasapiSettings(auto_convert=True)
    except Exception:
        pass
    return None


# Alias sémantique pour la sortie (même logique WASAPI).
output_extra_settings = input_extra_settings
