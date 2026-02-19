@echo off
TITLE Observer Health Check
echo Checking Observer and Registry health...
python -m mcp_inventory.cli health
echo.
pause
