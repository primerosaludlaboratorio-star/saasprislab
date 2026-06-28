@echo off
echo ================================================================================
echo CARGA DE INVENTARIO - FARMACIA PRISLAB
echo ================================================================================
echo.

echo [PASO 1] Buscando archivo de productos...
echo.

REM Buscar archivo con el patrón
for %%f in (Productos-farmacia*.xlsx Productos-farmacia*.xls productos-farmacia*.xlsx productos-farmacia*.xls) do (
    if exist "%%f" (
        set ARCHIVO=%%f
        goto :found
    )
)

echo [ERROR] No se encontro el archivo de productos.
echo.
echo Asegurate de copiar el archivo a esta carpeta:
echo %CD%
echo.
echo El archivo debe tener un nombre como:
echo   - Productos-farmacia-2026-02-10-10-31.xlsx
echo   - Productos-farmacia.xlsx
echo.
pause
exit /b 1

:found
echo [OK] Archivo encontrado: %ARCHIVO%
echo.

echo [PASO 2] Activando entorno virtual...
call venv\Scripts\activate.bat

echo.
echo [PASO 3] Ejecutando carga de productos...
echo.
echo ================================================================================
python manage.py cargar_productos_farmacia "%ARCHIVO%"
echo ================================================================================

if errorlevel 1 (
    echo.
    echo [ERROR] La carga fallo. Revisar errores arriba.
    pause
    exit /b 1
)

echo.
echo [PASO 4] Verificando carga...
python manage.py shell -c "from core.models import Producto; print(f'\n[EXITO] Total de productos en sistema: {Producto.objects.count()}\n')"

echo.
echo ================================================================================
echo [COMPLETADO] Inventario cargado exitosamente
echo ================================================================================
echo.
echo Ahora puedes iniciar el servidor con:
echo   python manage.py runserver
echo.
pause
