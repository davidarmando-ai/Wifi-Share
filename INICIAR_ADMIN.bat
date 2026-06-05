@echo off
:: Reiniciar como administrador (necessário para ler senha do hotspot via netsh)
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Solicitando permissoes de administrador...
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    if exist "%temp%\getadmin.vbs" ( del "%temp%\getadmin.vbs" )
    pushd "%CD%"
    CD /D "%~dp0"

chcp 65001 >nul
title WiFi Share (Administrador)

echo ================================================
echo   WiFi Share — Modo Administrador
echo   (necessario para ler senha do hotspot)
echo ================================================
echo.

cd /d "%~dp0"

pip show flask >nul 2>&1
if errorlevel 1 (
    echo [*] A instalar Flask...
    pip install flask
)

netsh advfirewall firewall show rule name="WiFiShare" >nul 2>&1
if errorlevel 1 (
    netsh advfirewall firewall add rule name="WiFiShare" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1
)

echo [*] A iniciar servidor...
echo.
python iniciar.py

pause
