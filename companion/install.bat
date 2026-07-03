@echo off
REM ===========================================
REM  KAI Companion - Script de instalacion
REM ===========================================

setlocal enabledelayedexpansion

echo.
echo ======================================
echo   KAI Companion - Setup Assistant
echo ======================================
echo.

REM Verificar si Node.js esta instalado
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js no esta instalado
    echo.
    echo Descarga Node.js desde: https://nodejs.org/
    echo Recomendado: Version LTS (14+)
    echo.
    pause
    exit /b 1
)

echo [OK] Node.js detectado: 
node --version
echo.

REM Verificar npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm no esta instalado
    pause
    exit /b 1
)

echo [OK] npm detectado: 
npm --version
echo.

REM Crear directorios
echo [*] Creando directorios...
if not exist "data" mkdir data
if not exist "data\uploads" mkdir data\uploads
if not exist "data\tools" mkdir data\tools
if not exist "logs" mkdir logs
echo [OK] Directorios creados
echo.

REM Copiar .env.example a .env si no existe
if not exist ".env" (
    echo [*] Creando archivo .env...
    copy .env.example .env >nul
    echo [OK] .env creado
) else (
    echo [OK] .env ya existe
)
echo.

REM Instalar dependencias backend
echo [*] Instalando dependencias del backend...
call npm install
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de dependencias backend
    pause
    exit /b 1
)
echo [OK] Backend listo
echo.

REM Instalar dependencias frontend
echo [*] Instalando dependencias del frontend...
cd frontend
call npm install
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de dependencias frontend
    cd ..
    pause
    exit /b 1
)
cd ..
echo [OK] Frontend listo
echo.

echo ======================================
echo   Setup completado exitosamente!
echo ======================================
echo.
echo Proximos pasos:
echo   1. Ejecuta: npm run dev
echo   2. Abre: http://localhost:3000
echo.
pause
