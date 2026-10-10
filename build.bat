@echo off
setlocal EnableDelayedExpansion
echo =====================================================
echo   Smart File Organizer  ^|  Windows Build Script
echo =====================================================
echo.

rem Il launcher 'py' e' piu' affidabile di 'python' nel PATH, che su alcuni
rem sistemi punta all'interprete installato da un altro programma.
set PY=
where py >nul 2>&1 && set PY=py -3
if "%PY%"=="" (
    where python >nul 2>&1 && set PY=python
)
if "%PY%"=="" (
    echo [ERROR] Python non trovato. Installa Python 3.11+ da python.org
    pause & exit /b 1
)
echo [INFO] Interprete: %PY%

%PY% -m pip install pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] Installazione PyInstaller fallita.
    pause & exit /b 1
)

echo [BUILD] Compilazione in corso...
echo.

set ICON_FLAG=
if exist "assets\icon.ico" set ICON_FLAG=--icon=assets\icon.ico

rem --collect-all customtkinter e' obbligatorio: la libreria carica i propri
rem file di tema a runtime e senza questo il .exe parte e si chiude subito.
%PY% -m PyInstaller ^
    --noconsole ^
    --onefile ^
    %ICON_FLAG% ^
    --name=SmartFileOrganizer ^
    --collect-all customtkinter ^
    --add-data "assets;assets" ^
    main.py

echo.
if exist "dist\SmartFileOrganizer.exe" (
    echo [OK] Build completata con successo!
    echo      Output: dist\SmartFileOrganizer.exe
) else (
    echo [ERROR] Build fallita. Controlla l'output sopra.
)
echo.
pause
