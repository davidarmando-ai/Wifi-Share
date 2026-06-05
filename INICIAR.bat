@echo off
chcp 65001 >nul
title WiFi Share

echo ================================================
echo   WiFi Share — Iniciando servidor...
echo ================================================
echo.

:: Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo.
    echo Instale Python em: https://www.python.org/downloads/
    echo Certifique-se de marcar "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

:: Ir para a pasta do script
cd /d "%~dp0"

:: Instalar Flask se necessário
pip show flask >nul 2>&1
if errorlevel 1 (
    echo [*] A instalar Flask...
    pip install flask
)

:: Verificar se o Windows Firewall pode bloquear
echo [*] A verificar firewall...
netsh advfirewall firewall show rule name="WiFiShare" >nul 2>&1
if errorlevel 1 (
    echo [*] A adicionar regra de firewall para porta 5000...
    netsh advfirewall firewall add rule name="WiFiShare" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1
)

echo.
echo [*] A iniciar servidor...
echo.

:: Iniciar com privilégios (necessário para ler senha do hotspot)
python iniciar.py

pause
