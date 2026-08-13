@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  REINITIALISATION du Claude Copilot DCS
echo  Ramene le dossier a son etat minimal (juste les scripts).
echo  Seront SUPPRIMES (tout est re-telecharge au prochain run.bat) :
echo    - Cle(s) API        : apikey.txt, openai_key.txt
echo    - Configuration     : config.json
echo    - Python embarque   : python\
echo    - Librairies Python : libs\
echo    - Piper + voix      : piper\
echo    - Modeles Whisper   : models\
echo  (Le hook DCS dans Saved Games n'est PAS touche.)
echo ============================================================
choice /M "Confirmer la reinitialisation"
if errorlevel 2 goto :end

del /q "apikey.txt" 2>nul
del /q "openai_key.txt" 2>nul
del /q "config.json" 2>nul
if exist "libs" rmdir /s /q "libs"
if exist "models" rmdir /s /q "models"
if exist "piper" rmdir /s /q "piper"
if exist "python" rmdir /s /q "python"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo.
echo Reinitialisation terminee. Dossier minimal.
echo Relance run.bat : il re-telechargera Python, les librairies et Piper,
echo puis saisis ta cle API dans l'interface.
:end
echo.
pause
