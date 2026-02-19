#!/bin/bash
# Double-click to run Observer health check
echo "Checking Observer and Registry health..."
python3 -m mcp_inventory.cli health
echo ""
read -p "Press any key to exit..."
