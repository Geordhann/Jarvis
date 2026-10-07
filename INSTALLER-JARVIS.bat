@echo off
chcp 65001 >nul
title Installation de Jarvis
cd /d "%~dp0"
echo.
echo  ======================================
echo     INSTALLATION DE JARVIS (de zero)
echo  ======================================
echo.

echo [1/5] Arret de l'ancien Jarvis s'il tourne...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*-m jarvis*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

echo [2/5] Recherche de Python...
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
  echo.
  echo  Python est introuvable. Installe-le depuis https://www.python.org/downloads/
  echo  en cochant "Add python.exe to PATH", puis relance ce fichier.
  goto fin
)
%PY% --version

echo [3/5] Installation des composants (quelques minutes)...
if exist ".venv" rmdir /s /q ".venv"
%PY% -m venv .venv || goto erreur
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto erreur
echo.
choice /c ON /n /m "Installer aussi l'ecoute sur le PC (Whisper + Hey Jarvis, environ 500 Mo) ? [O/N] "
if errorlevel 2 goto reglages
".venv\Scripts\python.exe" -m pip install -r requirements-local.txt

:reglages
echo.
echo [4/5] Anciens reglages
echo  Ils sont dans %USERPROFILE%\.jarvis.json et %USERPROFILE%\.jarvis
echo  (cle, voix, connexion Google, notes, rappels, memoire).
choice /c ON /n /m "Tout effacer pour repartir de zero ? [O/N] "
if errorlevel 2 goto config
del /q "%USERPROFILE%\.jarvis.json" 2>nul
del /q "%USERPROFILE%\.jarvis.log" 2>nul
rmdir /s /q "%USERPROFILE%\.jarvis" 2>nul
echo  Anciens reglages effaces.

:config
echo.
echo [5/5] Configuration
".venv\Scripts\python.exe" -m jarvis --configurer || goto erreur
echo.
choice /c ON /n /m "Lancer Jarvis maintenant ? [O/N] "
if errorlevel 2 goto fin
start "" ".venv\Scripts\pythonw.exe" -m jarvis --fond
echo  Jarvis demarre (la boule apparait dans quelques secondes).
goto fin

:erreur
echo.
echo  *** Une etape a echoue. Fais une capture de cette fenetre et envoie-la. ***

:fin
echo.
pause
