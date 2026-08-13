"""Synthèse vocale via SAPI (win32com), avec choix de la voix ET de la sortie audio.

En VR, le casque n'est souvent PAS le périphérique par défaut de Windows : on
permet donc d'envoyer la voix de Claude sur un périphérique précis (ex. le casque
Oculus), sinon on ne l'entend pas dans le casque.
"""
import json
import os
import re
import subprocess

import numpy as np
import sounddevice as sd
import win32com.client

import audioio


# Phrases de test par langue (famille de code : fr, en, de...). Repli = en.
TEST_PHRASES = {
    "fr": "Copilote en ligne. Test de la voix, un deux trois.",
    "en": "Copilot online. Voice test, one two three.",
    "de": "Copilot online. Sprachtest, eins zwei drei.",
    "es": "Copiloto en línea. Prueba de voz, uno dos tres.",
    "it": "Copilota in linea. Prova della voce, uno due tre.",
    "pt": "Copiloto online. Teste de voz, um dois três.",
    "nl": "Copiloot online. Stemtest, één twee drie.",
    "ru": "Второй пилот на связи. Проверка голоса, раз два три.",
    "pl": "Drugi pilot online. Test głosu, raz dwa trzy.",
    "sv": "Andrepilot online. Rösttest, ett två tre.",
    "da": "Andenpilot online. Stemmetest, en to tre.",
    "no": "Andrepilot på linjen. Stemmetest, én to tre.",
    "fi": "Perämies linjoilla. Äänitesti, yksi kaksi kolme.",
    "tr": "Yardımcı pilot hazır. Ses testi, bir iki üç.",
    "cs": "Kopilot online. Test hlasu, jedna dva tři.",
    "ro": "Copilot online. Test vocal, unu doi trei.",
    "hu": "Másodpilóta online. Hangteszt, egy kettő három.",
    "el": "Συγκυβερνήτης σε σύνδεση. Δοκιμή φωνής, ένα δύο τρία.",
    "uk": "Другий пілот на зв'язку. Перевірка голосу, раз два три.",
    "ar": "الطيار المساعد على الخط. اختبار الصوت، واحد اثنان ثلاثة.",
    "zh": "副驾驶在线。语音测试，一二三。",
    "vi": "Phi công phụ trực tuyến. Kiểm tra giọng nói, một hai ba.",
}


def voice_language(cfg):
    """Famille de langue (fr, en, de...) de la voix TTS active."""
    if cfg.get("tts_engine") == "piper":
        p = cfg.get("piper_model_path") or ""
        m = re.match(r"([a-z]{2,3})[_-]", os.path.basename(p))
        if m:
            return m.group(1)
        try:
            with open(p + ".json", encoding="utf-8") as f:
                d = json.load(f)
            fam = (d.get("language", {}).get("family")
                   or d.get("espeak", {}).get("voice", ""))
            if fam:
                return fam.split("-")[0]
        except Exception:
            pass
    else:
        hint = (cfg.get("tts_voice_hint") or "").lower()
        for kw, fam in (("french", "fr"), ("english", "en"), ("german", "de"),
                        ("spanish", "es"), ("italian", "it"), ("dutch", "nl"),
                        ("russian", "ru")):
            if kw in hint:
                return fam
    return "en"


def test_phrase(cfg):
    """Phrase de test dans la langue de la voix sélectionnée."""
    return TEST_PHRASES.get(voice_language(cfg), TEST_PHRASES["en"])


def clean_for_speech(text):
    """Retire le markdown pour ne pas prononcer les astérisques, dièses, etc."""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)   # **gras**
    text = re.sub(r"\*(.*?)\*", r"\1", text)         # *italique*
    text = re.sub(r"`+", "", text)                    # `code`
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.M)  # puces
    text = re.sub(r"[*_#>]", "", text)                # symboles md résiduels
    text = re.sub(r"\s+", " ", text).strip()
    return text


def list_piper_voices(voices_dir):
    """Liste les voix Piper (*.onnx avec .json) présentes dans le dossier."""
    out = []
    if os.path.isdir(voices_dir):
        for f in sorted(os.listdir(voices_dir)):
            if f.endswith(".onnx") and os.path.isfile(os.path.join(voices_dir, f + ".json")):
                out.append({"name": f[:-5], "path": os.path.join(voices_dir, f)})
    return out


def list_outputs():
    """Liste les sorties audio SAPI (index + description)."""
    sp = win32com.client.Dispatch("SAPI.SpVoice")
    outs = sp.GetAudioOutputs()
    return [{"index": i, "name": outs.Item(i).GetDescription()}
            for i in range(outs.Count)]


class Speaker:
    def __init__(self, voice_hint=None, output_hint=None):
        self._sp = win32com.client.Dispatch("SAPI.SpVoice")
        if voice_hint:
            voices = self._sp.GetVoices()
            for i in range(voices.Count):
                v = voices.Item(i)
                if voice_hint.lower() in v.GetDescription().lower():
                    self._sp.Voice = v
                    break
        if output_hint:
            outs = self._sp.GetAudioOutputs()
            for i in range(outs.Count):
                o = outs.Item(i)
                if output_hint.lower() in o.GetDescription().lower():
                    self._sp.AudioOutput = o
                    break

    def say(self, text):
        self._sp.Speak(text)


class PiperSpeaker:
    """TTS neuronal local via Piper (piper.exe) — voix naturelle, CPU, GPU libre."""
    def __init__(self, exe, model, output_name=None):
        self.exe = exe
        self.model = model
        with open(model + ".json", encoding="utf-8") as f:
            self.sr = json.load(f)["audio"]["sample_rate"]
        self.device = audioio.resolve_output_device(output_name)

    def say(self, text):
        proc = subprocess.run(
            [self.exe, "-m", self.model, "--output-raw"],
            input=text.encode("utf-8"), capture_output=True,
            cwd=os.path.dirname(self.exe),
        )
        if proc.returncode != 0 or not proc.stdout:
            raise RuntimeError((proc.stderr or b"").decode("utf-8", "ignore")[:200]
                               or "piper: pas de sortie audio")
        audio = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(audio, samplerate=self.sr, device=self.device,
                extra_settings=audioio.output_extra_settings(self.device))
        sd.wait()


def make_speaker(cfg):
    """Fabrique le lecteur TTS selon la config. Repli SAPI si Piper indisponible."""
    if cfg.get("tts_engine") == "piper":
        exe = cfg.get("piper_exe_path")
        model = cfg.get("piper_model_path")
        if exe and model and os.path.isfile(exe) and os.path.isfile(model):
            return PiperSpeaker(exe, model, cfg.get("tts_output_name"))
        print("[tts] Piper introuvable, repli sur la voix SAPI.")
    return Speaker(cfg.get("tts_voice_hint"), cfg.get("tts_output_name"))
