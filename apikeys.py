"""Gestion des clés API par fournisseur (stockage fichier + variable d'env).

- Anthropic  -> apikey.txt      (var ANTHROPIC_API_KEY)
- OpenAI     -> openai_key.txt   (var OPENAI_API_KEY, ou cfg.llm_api_key_env)
- Ollama     -> aucune clé

La clé n'est affichée que masquée (3 premiers + 4 derniers caractères).
"""
import os

import dcs_config


def env_var(provider, cfg=None):
    if provider == "anthropic":
        return "ANTHROPIC_API_KEY"
    if provider == "ollama":
        return None
    return (cfg or {}).get("llm_api_key_env") or "OPENAI_API_KEY"


def key_file(provider):
    if provider == "anthropic":
        return os.path.join(dcs_config.HERE, "apikey.txt")
    if provider == "ollama":
        return None
    return os.path.join(dcs_config.HERE, "openai_key.txt")


def current_key(provider, cfg=None):
    """Clé courante : variable d'env sinon fichier. None si absente."""
    ev = env_var(provider, cfg)
    if ev and os.environ.get(ev):
        return os.environ[ev].strip()
    f = key_file(provider)
    if f and os.path.isfile(f):
        try:
            k = open(f, encoding="utf-8").read().strip()
            return k or None
        except Exception:
            return None
    return None


def load_into_env(provider, cfg=None):
    """Charge la clé du fichier dans la variable d'env si pas déjà définie."""
    ev = env_var(provider, cfg)
    if not ev or os.environ.get(ev):
        return os.environ.get(ev) if ev else None
    f = key_file(provider)
    if f and os.path.isfile(f):
        k = open(f, encoding="utf-8").read().strip()
        if k:
            os.environ[ev] = k
            return k
    return None


def save_key(provider, key, cfg=None):
    """Écrit la clé dans le fichier du fournisseur et l'applique à la variable d'env."""
    key = (key or "").strip()
    f = key_file(provider)
    if not f:
        raise ValueError("ce fournisseur ne nécessite pas de clé")
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(key)
    ev = env_var(provider, cfg)
    if ev:
        os.environ[ev] = key


def masked(key):
    if not key:
        return ""
    k = key.strip()
    if len(k) <= 8:
        return "•" * len(k)
    return k[:3] + "…" + k[-4:]


def needs_key(cfg):
    """True si le fournisseur courant exige une clé et qu'aucune n'est disponible."""
    prov = cfg.get("llm_provider", "anthropic")
    if prov == "ollama":
        return False
    return not current_key(prov, cfg)
