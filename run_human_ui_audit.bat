@echo off
setlocal
pushd "%~dp0"
npm run human:ui -- %*
set EXITCODE=%ERRORLEVEL%
popd
exit /b %EXITCODE%
