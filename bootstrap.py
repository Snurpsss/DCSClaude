"""Installation des librairies Python au 1er démarrage (dossier libs/).

Lancé par run.bat quand libs/.installed est absent. N'utilise QUE la stdlib
(les libs ne sont pas encore là). pip est fourni avec le Python embarqué.
"""
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
LIBS = os.path.join(HERE, "libs")
PYDIR = os.path.join(HERE, "python")
PY = os.path.join(PYDIR, "python.exe")
MARKER = os.path.join(LIBS, ".installed")
REQ = os.path.join(HERE, "requirements.txt")

PIPER_DIR = os.path.join(HERE, "piper")
PIPER_EXE = os.path.join(PIPER_DIR, "piper", "piper.exe")
PIPER_URL = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"
VOICE_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium"


def _download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "dcs-claude-copilot"})
    tmp = dest + ".part"
    with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    os.replace(tmp, dest)


def install_libs():
    if os.path.exists(MARKER):
        return True
    print("=== Installation des librairies Python (quelques minutes) ===\n")
    os.makedirs(LIBS, exist_ok=True)
    env = dict(os.environ, HF_HUB_DISABLE_SYMLINKS="1",
               HF_HUB_DISABLE_SYMLINKS_WARNING="1")
    try:
        subprocess.check_call(
            [PY, "-m", "pip", "install", "--target", LIBS,
             "--no-warn-script-location", "-r", REQ], env=env)
    except subprocess.CalledProcessError as e:
        print(f"\nÉCHEC de l'installation pip ({e}). Vérifie ta connexion.")
        return False
    # pywin32 : ses DLLs doivent être à côté de python.exe (sinon win32com casse).
    sysdir = os.path.join(LIBS, "pywin32_system32")
    if os.path.isdir(sysdir):
        for f in os.listdir(sysdir):
            if f.lower().endswith(".dll"):
                try:
                    shutil.copy2(os.path.join(sysdir, f), os.path.join(PYDIR, f))
                except Exception:
                    pass
    with open(MARKER, "w", encoding="utf-8") as fh:
        fh.write("ok")
    print("\n=== Librairies installées. ===")
    return True


def install_piper():
    if os.path.isfile(PIPER_EXE):
        return True
    print("\n=== Installation de Piper (voix) ===")
    os.makedirs(PIPER_DIR, exist_ok=True)
    try:
        z = os.path.join(PIPER_DIR, "_piper.zip")
        print("Telechargement du binaire Piper...")
        _download(PIPER_URL, z)
        with zipfile.ZipFile(z) as zf:
            zf.extractall(PIPER_DIR)
        os.remove(z)
        vd = os.path.join(PIPER_DIR, "voices")
        os.makedirs(vd, exist_ok=True)
        print("Telechargement de la voix par defaut (fr_FR-siwis)...")
        for ext in (".onnx.json", ".onnx"):
            dest = os.path.join(vd, "fr_FR-siwis-medium" + ext)
            if not os.path.isfile(dest):
                _download(VOICE_BASE + "/fr_FR-siwis-medium" + ext, dest)
    except Exception as e:
        print(f"AVERTISSEMENT : installation de Piper échouée ({e}). "
              "La voix SAPI (Windows) sera utilisée en repli.")
        return False
    print("=== Piper prêt. ===")
    return True


def main():
    ok = install_libs()
    if not ok:
        return 1
    install_piper()   # non bloquant : repli SAPI si échec
    return 0


if __name__ == "__main__":
    sys.exit(main())
