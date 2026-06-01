@echo off
echo ================================================================================
echo PRISLAB GOLD - INICIO DE PRUEBAS CLINICAS
echo ================================================================================
echo.

echo [1/3] Activando entorno virtual...
call venv\Scripts\activate.bat

echo.
echo [2/3] Verificando sistema...
python verificar_sistema.py

if errorlevel 1 (
    echo.
    echo [ERROR] Sistema no pasa verificacion. Revisar advertencias.
    echo Presione cualquier tecla para continuar de todos modos...
    pause
)

echo.
echo [3/3] Iniciando servidor Django...
echo.
echo ================================================================================
echo SERVIDOR LISTO EN: http://127.0.0.1:8000
echo ================================================================================
echo.
echo URLs IMPORTANTES:
echo   - Admin:       http://127.0.0.1:8000/admin/
echo   - Consultorio: http://127.0.0.1:8000/consultorio/
echo   - Farmacia:    http://127.0.0.1:8000/farmacia/
echo   - Laboratorio: http://127.0.0.1:8000/laboratorio/
echo.
echo Presione Ctrl+C para detener el servidor
echo ================================================================================
echo.

python manage.py runserver
