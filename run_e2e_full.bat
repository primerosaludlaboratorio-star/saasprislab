@echo off
setlocal EnableDelayedExpansion

REM Start Django server with SSL disabled for E2E
cd C:\Users\jonil\Desktop\PRISLAB_SaaS-master\PRISLAB_SaaS-master
set E2E_DISABLE_SSL=1
start /MIN "Django Server" .venv\Scripts\python.exe manage.py runserver 8000 --noreload

REM Wait for server to start
echo Waiting for server...
timeout /t 5 /nobreak >nul

REM Run E2E suite with credentials
set E2E_USER=e2e_admin
set E2E_PASS=e2e_test_pass_123
set PDV_USER=e2e_admin
set PDV_PASS=e2e_test_pass_123
set OMNI_PRELOGIN=1

npm run omni:local -- --headless

REM Kill server
taskkill /F /IM python.exe 2>nul
