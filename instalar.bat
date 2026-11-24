@echo off
rem Instala el DevPanel: crea carpetas, comprueba Python y genera iniciar_devpanel.bat y detener_devpanel.bat
cd /d "%~dp0"
where py >nul 2>nul && (py -3 instalar.py %* & goto fin)
where python >nul 2>nul && (python instalar.py %* & goto fin)
echo No encuentro Python. Instala Python 3.10 o superior desde python.org y vuelve a ejecutar este archivo.
:fin
pause
