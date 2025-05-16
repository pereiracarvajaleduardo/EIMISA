@echo off
echo Iniciando el servidor Flask y abriendo el navegador...

REM Cambia al directorio donde se encuentra este script .bat
cd /d "%~dp0"

REM Verifica si Python está instalado (opcional, pero útil para feedback)
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no parece estar instalado o no está en el PATH.
    pause
    exit /b 1
)

REM Verifica si Flask está instalado (basado en requirements.txt)
pip show Flask >nul 2>&1
if %errorlevel% neq 0 (
    echo Flask no está instalado. Intentando instalar desde requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo instalar Flask. Por favor, instálalo manualmente.
        pause
        exit /b 1
    )
)

echo Ejecutando el servidor Flask (app.py)...
REM Inicia el servidor Flask en una nueva ventana de consola
REM Esto permite que este script .bat continúe y abra el navegador
start "Flask Server" cmd /k "python app.py"

echo Esperando un momento para que el servidor se inicie completamente...
REM Espera 5 segundos. Puedes ajustar este tiempo si es necesario.
timeout /t 5 /nobreak > nul

echo Abriendo la interfaz web en tu navegador predeterminado...
start http://localhost:5000

echo.
echo El servidor Flask debería estar ejecutándose en una nueva ventana.
echo Puedes acceder a tus PDFs en http://localhost:5000 en tu PC.
echo Para acceder desde tu celular (misma red Wi-Fi), usa la IP de tu PC, por ejemplo: http://TU_IP_LOCAL:5000
echo (Puedes encontrar tu IP local escribiendo 'ipconfig' en otra ventana de comandos).
echo.
echo Para detener el servidor, cierra la ventana de la consola titulada "Flask Server".

pause