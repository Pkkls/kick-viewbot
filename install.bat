@echo off
REM ============================================================
REM Installation Dashboard Kick Viewbot VM Control - Windows
REM ============================================================

echo ============================================================
echo Installation Dashboard Kick Viewbot VM Control
echo ============================================================
echo.

REM Vérification Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH !
    echo Telecharge Python sur : https://www.python.org/downloads/
    echo N'oublie pas de cocher "Add Python to PATH" lors de l'installation
    pause
    exit /b 1
)

echo [OK] Python detecte : 
python --version

REM Création du dossier
set INSTALL_DIR=%USERPROFILE%\kick-vm-control
echo.
echo Creation du dossier : %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"

REM Création du venv
echo.
echo Creation de l'environnement virtuel Python...
if exist venv rmdir /s /q venv
python -m venv venv

REM Activation et installation des dépendances
echo.
echo Installation des dependances...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install flask flask-cors paramiko --quiet

echo [OK] Dependances installees : flask, flask-cors, paramiko

REM Création de server.py (le contenu sera inséré ici)
echo.
echo Creation du serveur API...

REM Le fichier server.py sera créé séparément
echo Configuration terminee !

echo.
echo ============================================================
echo Installation terminee avec succes !
echo ============================================================
echo.
echo Prochaines etapes :
echo.
echo 1. Copie ton fichier kick.py dans : %INSTALL_DIR%
echo.
echo 2. Lance le serveur avec : start.bat
echo.
echo 3. Ouvre ton navigateur sur : http://192.168.1.6:5000
echo.
echo ============================================================
pause