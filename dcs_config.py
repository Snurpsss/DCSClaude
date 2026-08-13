"""Configuration partagée entre l'interface (configurator.py) et l'app (copilot.py)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
MODELS_DIR = os.path.join(HERE, "models")
PIPER_VOICES_DIR = os.path.join(HERE, "piper", "voices")

# Langues d'interaction (code Whisper + libellé). Whisper est multilingue :
# un seul modèle gère toutes ces langues (rien à télécharger par langue pour la STT).
SPOKEN_LANGUAGES = [
    {"code": "fr", "label": "Français"},
    {"code": "en", "label": "English"},
    {"code": "de", "label": "Deutsch"},
    {"code": "es", "label": "Español"},
    {"code": "it", "label": "Italiano"},
    {"code": "pt", "label": "Português"},
    {"code": "nl", "label": "Nederlands"},
    {"code": "ru", "label": "Русский"},
    {"code": "pl", "label": "Polski"},
    {"code": "sv", "label": "Svenska"},
    {"code": "da", "label": "Dansk"},
    {"code": "no", "label": "Norsk"},
    {"code": "fi", "label": "Suomi"},
    {"code": "tr", "label": "Türkçe"},
    {"code": "cs", "label": "Čeština"},
    {"code": "ro", "label": "Română"},
    {"code": "hu", "label": "Magyar"},
    {"code": "el", "label": "Ελληνικά"},
    {"code": "uk", "label": "Українська"},
    {"code": "ar", "label": "العربية"},
    {"code": "zh", "label": "中文"},
    {"code": "ja", "label": "日本語"},
    {"code": "ko", "label": "한국어"},
    {"code": "vi", "label": "Tiếng Việt"},
]
# Nom de langue injecté dans le prompt (pour la langue des réponses de Claude).
LANG_NAMES = {l["code"]: l["label"] for l in SPOKEN_LANGUAGES}

DEFAULTS = {
    # Push-to-talk : type "keyboard" ou "joystick"
    "ptt": {"type": "keyboard", "key": "right ctrl", "label": "Ctrl droit"},
    # Micro : index du périphérique sounddevice (None = défaut système)
    "mic_device": None,
    "mic_device_name": "",
    # Reconnaissance vocale
    "whisper_model": "small",
    "whisper_device": "cpu",     # "cpu" ou "cuda"
    "whisper_compute": "int8",   # "int8" (cpu) ou "float16" (gpu)
    "language": "fr",
    # Cerveau (LLM) — interchangeable
    "llm_provider": "anthropic",   # "anthropic" | "openai" | "ollama"
    "llm_model": "",               # vide = défaut du fournisseur
    "llm_base_url": "",            # vide = défaut (ollama: http://localhost:11434/v1)
    "llm_api_key_env": "OPENAI_API_KEY",  # variable d'env de la clé (openai/custom)
    "claude_model": "claude-sonnet-4-6",  # modèle Anthropic par défaut
    # Moteur de synthèse : "piper" (neuronal local) ou "sapi" (voix Windows)
    "tts_engine": "piper",
    "piper_exe_path": os.path.join(HERE, "piper", "piper", "piper.exe"),
    "piper_model_path": os.path.join(HERE, "piper", "voices", "fr_FR-siwis-medium.onnx"),
    # Voix de synthèse SAPI (sous-chaîne du nom à préférer, si moteur = sapi)
    "tts_voice_hint": "french",
    # Sortie audio du TTS (sous-chaîne du nom de périphérique ; vide = défaut)
    "tts_output_name": "",
    # Mode de sortie voix : "headset" (SAPI local) ou "srs" (radio en jeu)
    "voice_mode": "headset",
    # DCS-SRS (radio en jeu) — chemin vers DCS-SRS-ExternalAudio.exe
    "srs_exe_path": "",
    "srs_freq": "251",         # MHz
    "srs_modulation": "AM",    # AM / FM
    "srs_coalition": 2,        # 1 rouge, 2 bleu
    "srs_port": 5002,
    "srs_ip": "127.0.0.1",
    "srs_culture": "fr-FR",
    "srs_voice": "",
    # Canal de commande vers DCS (hook Lua ; "none" pour désactiver)
    "control_backend": "hook",
    "display_responses": True,   # afficher les réponses de Claude à l'écran DCS
    "control_host": "127.0.0.1",
    "control_port": 5011,        # port du hook Lua
    # Multi-persona : plusieurs opérateurs, chacun sa voix/langue/fréquence/rôle.
    "personas": [
        {"id": "magic", "callsign": "Magic", "freq": "305.0", "language": "fr",
         "voice": os.path.join(PIPER_VOICES_DIR, "fr_FR-siwis-medium.onnx"),
         "role": "operator", "enabled": True},
        {"id": "overlord", "callsign": "Overlord", "freq": "251.0", "language": "fr",
         "voice": os.path.join(PIPER_VOICES_DIR, "fr_FR-tom-medium.onnx"),
         "role": "awacs", "enabled": True},
        {"id": "two", "callsign": "IceMan", "freq": "133.0", "language": "fr",
         "voice": os.path.join(PIPER_VOICES_DIR, "fr_FR-siwis-medium.onnx"),
         "role": "wingman", "enabled": True},
    ],
    "active_persona": "magic",   # persona par défaut si aucun indicatif détecté
    # Adressage des personas :
    "ptt_mode": "global",        # "global" (un seul PTT) ou "per_persona" (un PTT par persona)
    "freq_required": False,      # True = il FAUT être sur la fréquence du persona pour le joindre
}


def load():
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            print(f"[config] lecture impossible ({e}), valeurs par défaut.")
    return cfg


def save(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
