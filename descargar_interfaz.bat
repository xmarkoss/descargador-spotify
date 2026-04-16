@echo off
:: Accedemos al entorno virtual
call venv\Scripts\activate.bat

:: 'pythonw' es la versión de Python que no abre consola
:: 'start' lanza el proceso de forma independiente
start pythonw src/gui.py

:: Cerramos el archivo .bat inmediatamente
exit