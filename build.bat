@echo off
title Compilador Spotify Master Suite
color 0A

echo ====================================================
echo      CONSTRUYENDO SPOTIFY MASTER SUITE v9.0
echo ====================================================
echo.

:: 1. Activar el entorno virtual si existe
if exist venv\Scripts\activate.bat (
    echo [*] Activando entorno virtual...
    call venv\Scripts\activate.bat
)

:: 2. Ejecutar PyInstaller con el icono
echo [*] Compilando codigo fuente a .exe...
python -m PyInstaller --noconsole --onefile --icon="assets/icon.ico" --name "SpotifyMasterSuite" src/gui.py

:: 3. Copiar las dependencias a la carpeta final (dist)
echo.
echo [*] Empaquetando motores y recursos...
:: /E (copia subcarpetas), /I (asume que el destino es carpeta), /Y (sobrescribe sin preguntar)
xcopy /E /I /Y "ffmpeg" "dist\ffmpeg"
xcopy /E /I /Y "assets" "dist\assets"

:: 4. Limpieza de archivos temporales (Mantenemos el proyecto limpio)
echo.
echo [*] Limpiando archivos temporales...
rmdir /s /q build
del /q SpotifyMasterSuite.spec

echo.
echo ====================================================
echo   [✔] COMPILACION EXITOSA
echo   Tu producto final esta listo en la carpeta 'dist'
echo ====================================================
pause