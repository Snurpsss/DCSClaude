"""Transmission de la voix de Claude PAR LA RADIO DCS via DCS-SRS.

Utilise DCS-SRS-ExternalAudio.exe (fourni avec DCS-SRS) : on lui passe le texte
et une fréquence ; il synthétise un TTS et le transmet sur le réseau SRS. En jeu,
avec le client SRS connecté et la radio réglée sur cette fréquence, tu entends
Claude sur la radio.

Prérequis côté joueur :
  - DCS-SRS installé,
  - un serveur SRS joignable (SR-Server.exe en local pour le solo),
  - le client SRS lancé et connecté, radio de l'appareil réglée sur la fréquence.
"""
import os
import subprocess


def available(cfg):
    p = cfg.get("srs_exe_path") or ""
    return bool(p) and os.path.isfile(p)


def build_args(cfg, text):
    exe = cfg["srs_exe_path"]
    args = [
        exe,
        "-t", text,
        "-f", str(cfg.get("srs_freq", "251")),        # MHz
        "-m", cfg.get("srs_modulation", "AM"),         # AM / FM
        "-c", str(cfg.get("srs_coalition", 2)),        # 1 rouge, 2 bleu
        "-p", str(cfg.get("srs_port", 5002)),          # port serveur SRS
        "-i", cfg.get("srs_ip", "127.0.0.1"),
        "-v", "1.0",
        "-n", "Claude",
    ]
    if cfg.get("srs_culture"):
        args += ["--culture", cfg["srs_culture"]]      # ex. fr-FR
    if cfg.get("srs_voice"):
        args += ["--voice", cfg["srs_voice"]]
    return args


def transmit(cfg, text):
    """Transmet le texte sur la radio SRS. Lève une exception en cas d'échec."""
    if not available(cfg):
        raise RuntimeError("DCS-SRS-ExternalAudio.exe introuvable (chemin non configuré).")
    args = build_args(cfg, text)
    proc = subprocess.run(args, cwd=os.path.dirname(cfg["srs_exe_path"]),
                          capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"SRS a échoué (code {proc.returncode}) : "
                           f"{(proc.stderr or proc.stdout or '').strip()[:300]}")
