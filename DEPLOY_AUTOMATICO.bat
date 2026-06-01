@echo off
chcp 65001 >nul
color 0A
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║         DESPLIEGUE AUTOMÁTICO PRISLAB v5.0                     ║
echo ║         Railway + GitHub - Script Totalmente Automatizado      ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo [INFO] Iniciando proceso de despliegue automático...
echo.

:: Paso 1: Verificar Git
echo [1/6] Verificando Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git no está instalado. Instálalo desde: https://git-scm.com
    pause
    exit /b 1
)
echo [✓] Git instalado correctamente
echo.

:: Paso 2: Verificar que estamos en el directorio correcto
echo [2/6] Verificando directorio del proyecto...
if not exist "manage.py" (
    echo [ERROR] No se encuentra manage.py. Ejecuta este script desde la raíz del proyecto.
    pause
    exit /b 1
)
echo [✓] Directorio correcto
echo.

:: Paso 3: Mostrar instrucciones para GitHub
echo [3/6] Configuración de GitHub
echo.
echo ┌────────────────────────────────────────────────────────────────┐
echo │ PASO MANUAL REQUERIDO: Crear repositorio en GitHub            │
echo ├────────────────────────────────────────────────────────────────┤
echo │                                                                │
echo │ 1. Ve a: https://github.com/new                              │
echo │ 2. Nombre del repositorio: PRISLAB_SaaS                       │
echo │ 3. Privado o Público (tu elección)                           │
echo │ 4. NO inicialices con README                                  │
echo │ 5. Click en "Create repository"                               │
echo │                                                                │
echo │ Cuando tengas la URL del repositorio, cópiala.               │
echo │ Ejemplo: https://github.com/tu-usuario/PRISLAB_SaaS.git      │
echo │                                                                │
echo └────────────────────────────────────────────────────────────────┘
echo.
set /p REPO_URL="Pega aquí la URL de tu repositorio de GitHub: "

if "%REPO_URL%"=="" (
    echo [ERROR] No ingresaste la URL del repositorio
    pause
    exit /b 1
)

echo.
echo [✓] URL recibida: %REPO_URL%
echo.

:: Paso 4: Configurar remote y push
echo [4/6] Conectando con GitHub y subiendo código...

:: Verificar si ya existe remote
git remote remove origin >nul 2>&1

:: Agregar nuevo remote
git remote add origin %REPO_URL%
if errorlevel 1 (
    echo [ERROR] No se pudo agregar el remote
    pause
    exit /b 1
)

:: Cambiar a main
git branch -M main

:: Push
echo [INFO] Subiendo código a GitHub (esto puede tardar 1-2 minutos)...
git push -u origin main
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo hacer push. Posibles causas:
    echo   - No has autenticado con GitHub
    echo   - La URL del repositorio es incorrecta
    echo   - No tienes permisos en el repositorio
    echo.
    echo Solución: Configura Git con:
    echo   git config --global user.name "Tu Nombre"
    echo   git config --global user.email "tu@email.com"
    echo.
    echo Y autentícate con:
    echo   - Git Credential Manager (Windows)
    echo   - O crea un Personal Access Token en GitHub
    pause
    exit /b 1
)

echo [✓] Código subido a GitHub exitosamente
echo.

:: Paso 5: Instrucciones para Railway
echo [5/6] Instrucciones para Railway
echo.
echo ┌────────────────────────────────────────────────────────────────┐
echo │ PASO MANUAL REQUERIDO: Desplegar en Railway                   │
echo ├────────────────────────────────────────────────────────────────┤
echo │                                                                │
echo │ 1. Ve a: https://railway.app                                 │
echo │ 2. Click "Login with GitHub"                                  │
echo │ 3. Autoriza Railway                                           │
echo │ 4. Click "New Project"                                        │
echo │ 5. Selecciona "Deploy from GitHub repo"                       │
echo │ 6. Busca "PRISLAB_SaaS" y selecciónalo                       │
echo │ 7. Railway empezará a deployar automáticamente               │
echo │                                                                │
echo │ 8. Mientras deploya, agrega PostgreSQL:                      │
echo │    - Click "+ New" en tu proyecto                            │
echo │    - Selecciona "Database" → "Add PostgreSQL"                │
echo │                                                                │
echo │ 9. Configura variables de entorno:                           │
echo │    - Click en tu servicio → pestaña "Variables"              │
echo │    - Agrega estas variables:                                  │
echo │                                                                │
echo │      SECRET_KEY=prislab-secret-key-2026-cambiar-en-prod      │
echo │      DEBUG=False                                              │
echo │      ALLOWED_HOSTS=*.up.railway.app                          │
echo │      GOOGLE_API_KEY=(tu API key de Gemini)                   │
echo │      GOOGLE_CLOUD_PROJECT=prislab-v5-ai                      │
echo │                                                                │
echo │ 10. Railway detecta automáticamente la configuración         │
echo │     (railway.json, nixpacks.toml, Procfile)                  │
echo │                                                                │
echo │ 11. Espera 3-5 minutos para que complete el deploy           │
echo │                                                                │
echo │ 12. Obtén tu URL en Settings → Networking                    │
echo │     Ejemplo: https://prislab-production.up.railway.app       │
echo │                                                                │
echo └────────────────────────────────────────────────────────────────┘
echo.
pause

:: Paso 6: Finalización
echo.
echo [6/6] Finalizando...
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    ✅ PROCESO COMPLETADO                        ║
echo ╠════════════════════════════════════════════════════════════════╣
echo ║                                                                ║
echo ║  Tu código está en GitHub: %REPO_URL%
echo ║                                                                ║
echo ║  Siguiente paso:                                              ║
echo ║  1. Termina el deploy en Railway (sigue las instrucciones)   ║
echo ║  2. Cuando esté listo, accede a tu URL                       ║
echo ║  3. Login con: admin / PrislabV5_2026                        ║
echo ║                                                                ║
echo ║  📚 Documentación completa en:                                ║
echo ║     - README.md                                               ║
echo ║     - DEPLOY_RAILWAY_RAPIDO.md                               ║
echo ║     - INSTRUCCIONES_RAILWAY.md                               ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo Presiona cualquier tecla para salir...
pause >nul
