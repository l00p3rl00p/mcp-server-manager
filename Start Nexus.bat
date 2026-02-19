@echo off
setlocal
set PROJECT_DIR=%~dp0
echo 🚀 Starting Workforce Nexus...
echo 📍 Project: %PROJECT_DIR%

:: 1. Activate Environment
if exist "%PROJECT_DIR%..\.mcp-tools\Scripts\activate.bat" (
    echo 🐍 Using Virtual Environment
    call "%PROJECT_DIR%..\.mcp-tools\Scripts\activate.bat"
)

:: 2. Launch Tray & Bridge
cd /d "%PROJECT_DIR%"
echo 🔗 URL: http://localhost:5001
echo 📦 Look for the Indigo dot in your system tray.
echo ------------------------------------------------

:: Use 'start' so the batch window can close
start "" python nexus_tray.py
