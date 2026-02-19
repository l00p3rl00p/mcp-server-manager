#!/bin/bash
# Double-click to list connected MCP servers
echo "Fetching server list..."
mcp-observer list
read -p "Press any key to exit..."
