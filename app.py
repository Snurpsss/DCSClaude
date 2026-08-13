"""
Point d'entrée UNIQUE du Claude Copilot DCS.

Lance en même temps :
  - l'interface web de configuration (http://127.0.0.1:5001), et
  - la boucle du copilote,
qui partagent la même config en mémoire (core.py) -> réglages à la volée.

Lancé par run.bat.
"""
import os
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import threading
import webbrowser

import core
import configurator
import copilot

URL = "http://127.0.0.1:5001"


def _serve():
    # use_reloader=False : indispensable hors du thread principal.
    configurator.app.run(host="127.0.0.1", port=5001, threaded=True, use_reloader=False)


def main():
    # Charge la clé API du fournisseur courant (fichier -> variable d'env).
    import apikeys
    _cfg = core.get_config()
    apikeys.load_into_env(_cfg.get("llm_provider", "anthropic"), _cfg)
    # Interface web en tâche de fond.
    threading.Thread(target=_serve, daemon=True).start()
    # Précharge Whisper (pas d'attente au 1er test / 1re phrase).
    threading.Thread(target=core.preload_whisper, daemon=True).start()
    threading.Timer(1.0, lambda: webbrowser.open(URL)).start()
    print(f"Interface de configuration : {URL}")
    # Boucle du copilote sur le thread principal (clavier/audio globaux).
    copilot.run_copilot()


if __name__ == "__main__":
    main()
