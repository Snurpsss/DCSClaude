"""Cœur partagé entre l'interface web et la boucle du copilote.

Un seul état en mémoire (config + composants). L'interface modifie la config,
la boucle du copilote relit tout à chaque tour -> changements À LA VOLÉE.
Les composants lourds (Whisper, voix, gRPC) ne sont reconstruits que si leurs
réglages ont changé.
"""
import threading

import dcs_config
import ptt
import tts

STATE = {
    "config": dcs_config.load(),
    "cfg_lock": threading.Lock(),
    "monitor": None,
    "capture_lock": threading.Lock(),
    "whisper": None, "whisper_key": None, "whisper_lock": threading.Lock(),
    "stt_lock": threading.Lock(),
    "speaker": None, "speaker_key": None,
    "speak_lock": threading.Lock(),
    "control": None, "control_key": None,
}
STATE["monitor"] = ptt.PTTMonitor(STATE["config"].get("ptt"))


def get_config():
    """Instantané cohérent de la config (copie superficielle sous verrou)."""
    with STATE["cfg_lock"]:
        return dict(STATE["config"])


def update_config(partial):
    """Applique et persiste des changements ; réaligne les composants live."""
    with STATE["cfg_lock"]:
        STATE["config"].update(partial)
        dcs_config.save(STATE["config"])
        STATE["monitor"].rebind(STATE["config"].get("ptt"))
    return get_config()


def get_whisper():
    from faster_whisper import WhisperModel
    c = get_config()
    key = (c["whisper_model"], c["whisper_device"], c["whisper_compute"])
    with STATE["whisper_lock"]:
        if STATE["whisper_key"] != key:
            STATE["whisper"] = WhisperModel(
                c["whisper_model"], device=c["whisper_device"],
                compute_type=c["whisper_compute"], download_root=dcs_config.MODELS_DIR)
            STATE["whisper_key"] = key
        return STATE["whisper"]


def transcribe(audio, language):
    """Transcription sérialisée (évite les appels concurrents test/boucle)."""
    model = get_whisper()
    with STATE["stt_lock"]:
        segments, _ = model.transcribe(
            audio, language=language, vad_filter=True,
            beam_size=1, condition_on_previous_text=False)
        return " ".join(s.text for s in segments).strip()


def get_speaker():
    """(Re)construit le lecteur TTS si le moteur/voix/sortie a changé."""
    c = get_config()
    key = (c.get("tts_engine"), c.get("tts_voice_hint"), c.get("tts_output_name"),
           c.get("piper_exe_path"), c.get("piper_model_path"))
    if STATE["speaker_key"] != key:
        STATE["speaker"] = tts.make_speaker(c)
        STATE["speaker_key"] = key
    return STATE["speaker"]


def speak(text):
    """Lecture TTS sérialisée (évite les lectures audio concurrentes)."""
    with STATE["speak_lock"]:
        get_speaker().say(text)


def get_speaker_for(voice_path):
    """Lecteur Piper dédié à une voix (une par persona), mis en cache.
    Repli SAPI si la voix/Piper est indisponible."""
    import os
    c = get_config()
    cache = STATE.setdefault("speakers", {})
    out = c.get("tts_output_name")
    key = (voice_path, out, c.get("piper_exe_path"))
    if key not in cache:
        exe = c.get("piper_exe_path")
        if voice_path and os.path.isfile(voice_path) and exe and os.path.isfile(exe):
            cache[key] = tts.PiperSpeaker(exe, voice_path, out)
        else:
            cache[key] = tts.Speaker(c.get("tts_voice_hint"), out)
    return cache[key]


def speak_as(voice_path, text):
    """Parle avec la voix (persona) donnée, lecture sérialisée."""
    with STATE["speak_lock"]:
        get_speaker_for(voice_path).say(text)


def _close_control():
    if STATE["control"]:
        try:
            STATE["control"].close()
        except Exception:
            pass
    STATE["control"] = None
    STATE["control_key"] = None


def get_control():
    """Client de commande DCS (hook Lua) live. None si control_backend == 'none'.
    Interface : .ping() / .out_text() / .spawn_* / .order_engage() / .close()."""
    c = get_config()
    if c.get("control_backend", "hook") == "none":
        _close_control()
        return None
    key = ("hook", c.get("control_host", "127.0.0.1"), int(c.get("control_port", 5011)))
    if STATE["control"] is None or STATE["control_key"] != key:
        _close_control()
        try:
            import dcs_control
            STATE["control"] = dcs_control.DcsControl(key[1], key[2])
            STATE["control_key"] = key
        except Exception as e:
            print(f"[control] init échec : {e}")
            STATE["control"] = None
    return STATE["control"]


def get_llm():
    """Client LLM live (Claude/OpenAI/Ollama), reconstruit si la config change.
    STATE['llm_key'] change quand le fournisseur/modèle change (pour vider les
    historiques côté copilote, formats d'historique incompatibles entre adaptateurs)."""
    import llm
    c = get_config()
    key = llm.client_key(c)
    if STATE.get("llm") is None or STATE.get("llm_key") != key:
        STATE["llm"] = llm.make_client(c)
        STATE["llm_key"] = key
    return STATE["llm"]


def preload_whisper():
    try:
        get_whisper()
        print("Whisper préchargé.")
    except Exception as e:
        print(f"[whisper] préchargement différé : {e}")
