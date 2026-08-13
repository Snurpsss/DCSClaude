"""Catalogue COMPLET des voix Piper, basé sur l'index officiel voices.json.

Permet, comme https://rhasspy.github.io/piper-samples/ , de choisir une LANGUE
puis une VOIX, et de la télécharger en local dans piper\\voices\\.
"""
import json
import os
import threading
import urllib.request

import dcs_config

HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
INDEX_URL = f"{HF}/voices.json"

_lock = threading.Lock()
_index_cache = None


def _index(force=False):
    """Charge (et met en cache) l'index voices.json depuis HuggingFace."""
    global _index_cache
    with _lock:
        if _index_cache is None or force:
            req = urllib.request.Request(INDEX_URL, headers={"User-Agent": "dcs-claude"})
            with urllib.request.urlopen(req, timeout=60) as r:
                _index_cache = json.load(r)
        return _index_cache


def _installed():
    d = dcs_config.PIPER_VOICES_DIR
    if not os.path.isdir(d):
        return set()
    return {f[:-5] for f in os.listdir(d)
            if f.endswith(".onnx") and os.path.isfile(os.path.join(d, f + ".json"))}


def languages():
    """Liste des langues : [{code, label}] triée par nom anglais."""
    idx = _index()
    seen = {}
    for e in idx.values():
        lg = e["language"]
        code = lg["code"]
        if code not in seen:
            nat = lg.get("name_native", "")
            eng = lg.get("name_english", code)
            seen[code] = f"{eng} — {nat} ({code})" if nat else f"{eng} ({code})"
    return [{"code": c, "label": seen[c]} for c in sorted(seen, key=lambda c: seen[c].lower())]


def _onnx_size(entry):
    for p, meta in entry["files"].items():
        if p.endswith(".onnx"):
            return meta.get("size_bytes", 0)
    return 0


def voices_for(lang_code):
    """Voix d'une langue : [{key, label, installed}] triée par nom/qualité."""
    idx = _index()
    inst = _installed()
    out = []
    for key, e in idx.items():
        if e["language"]["code"] != lang_code:
            continue
        mb = round(_onnx_size(e) / (1024 * 1024))
        spk = e.get("num_speakers", 1)
        spk_txt = f", {spk} voix" if spk and spk > 1 else ""
        label = f"{e['name']} — {e['quality']} ({mb} Mo{spk_txt})"
        out.append({"key": key, "label": label, "installed": key in inst})
    out.sort(key=lambda v: v["key"])
    return out


def _fetch(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "dcs-claude-copilot"})
    tmp = dest + ".part"
    with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
    os.replace(tmp, dest)


def download(key):
    """Télécharge la voix `key` (son .onnx + .onnx.json). Renvoie le chemin .onnx."""
    e = _index().get(key)
    if not e:
        raise ValueError(f"voix inconnue : {key}")
    files = list(e["files"].keys())
    onnx = next(p for p in files if p.endswith(".onnx"))
    meta = next(p for p in files if p.endswith(".onnx.json"))
    d = dcs_config.PIPER_VOICES_DIR
    os.makedirs(d, exist_ok=True)
    dest_onnx = os.path.join(d, os.path.basename(onnx))
    _fetch(f"{HF}/{meta}", dest_onnx + ".json")   # petit fichier d'abord
    _fetch(f"{HF}/{onnx}", dest_onnx)              # gros modèle ensuite
    return dest_onnx
