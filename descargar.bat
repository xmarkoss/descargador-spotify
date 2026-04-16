@echo off
title Spotify Descargador PRO v6.0 - Launcher
color 0b

:: Configuración de rutas
set VENV_PATH=venv\Scripts\activate.bat
set SCRIPT_PATH=src\main.py

echo ===============================================
echo    INICIANDO INTERFAZ DE DESCARGA PRO
echo ===============================================

:: 1. Verificar si existe el entorno virtual
if not exist %VENV_PATH% (
    echo [X] ERROR: No se encontro el entorno virtual en \venv
    echo Por favor, asegúrate de estar en la carpeta raiz del proyecto.
    pause
    exit
)

:: 2. Activar el entorno virtual de forma silenciosa
call %VENV_PATH%

:: 3. Ejecutar el Master Suite
python %SCRIPT_PATH%

:: 4. Mantener la ventana abierta al finalizar
echo.
echo ===============================================
echo    PROCESO TERMINADO
echo ===============================================
pause