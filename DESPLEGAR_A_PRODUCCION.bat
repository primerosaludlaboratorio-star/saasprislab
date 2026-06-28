@echo off
REM ============================================================================
REM DESPLIEGUE COMPLETO DE PRISLAB A GOOGLE CLOUD
REM ============================================================================

echo ================================================================================
echo                 DESPLIEGUE PRISLAB A PRODUCCION
echo ================================================================================
echo.

REM ============================================================================
REM BLOQUE 1: SUBIR EL CODIGO (GIT)
REM ============================================================================
echo [BLOQUE 1] PREPARANDO CODIGO PARA SUBIR...
echo.

REM Verificar que git este instalado
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Git no esta instalado o no esta en el PATH
    echo.
    echo Por favor instala Git desde: https://git-scm.com/download/win
    echo O usa Git Bash para ejecutar los comandos manualmente
    echo.
    pause
    exit /b 1
)

REM Asegurar que los archivos CSV se incluyan
echo   - Agregando archivos CSV...
git add -f tarifas.csv
git add -f inventario.csv
git add -f Productos-farmacia-2026-02-10-10-31.csv
git add -f datos_lims\*.csv

REM Agregar todos los cambios
echo   - Agregando todos los archivos modificados...
git add .

REM Verificar que hay cambios
git diff --staged --quiet
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [AVISO] No hay cambios para commitear
    echo.
) else (
    REM Hacer commit
    echo   - Creando commit...
    git commit -m "DESPLIEGUE URGENTE: Farmacia, Lab Completo, Consultorio y Equipo"
    
    REM Push a la nube
    echo   - Enviando a Google Cloud...
    git push
    
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR] Fallo el push a Git
        echo Verifica tu conexion y credenciales
        pause
        exit /b 1
    )
    
    echo.
    echo [OK] Codigo subido exitosamente
)

echo.
echo ================================================================================
echo.
echo [IMPORTANTE] Ahora debes ejecutar los comandos en el SERVIDOR DE PRODUCCION
echo.
echo Conectate al servidor de Google Cloud y ejecuta:
echo.
echo   1. python manage.py migrate
echo   2. python manage.py migrar_lab_master
echo   3. python manage.py cargar_productos_csv Productos-farmacia-2026-02-10-10-31.csv
echo   4. python manage.py crear_equipo_oficial
echo   5. python manage.py collectstatic --noinput
echo.
echo O ejecuta el script: EJECUTAR_EN_SERVIDOR.sh
echo.
echo ================================================================================
pause
