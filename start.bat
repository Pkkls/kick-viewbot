@echo off
REM ============================================================
REM Demarrage du serveur Dashboard VM Control - Windows
REM ============================================================

cd /d %~dp0

echo ============================================================
echo Demarrage du serveur Kick Viewbot Control
echo ============================================================
echo.

REM Vérification du fichier kick.py
if not exist kick.py (
    echo [ERREUR] Le fichier kick.py est manquant !
    echo Copie ton fichier kick.py dans ce dossier : %CD%
    echo.
    pause
    exit /b 1
)

REM Activation du venv et démarrage
call venv\Scripts\activate.bat

echo [OK] Demarrage du serveur sur http://192.168.1.6:5000
echo.
echo Appuie sur Ctrl+C pour arreter le serveur
echo ============================================================
echo.

python server.py

pause