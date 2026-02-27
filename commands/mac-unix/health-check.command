#!/bin/bash
# Double-click to run Observer health check
echo "Checking Observer and Registry health..."
"$HOME/.mcp-tools/bin/mcp-observer" health
echo ""
read -p "Press any key to exit..."
