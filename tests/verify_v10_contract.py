import requests
import sys
import json

try:
    print("📉 Verifying V10 Metric Telemetry...")
    
    # 1. Test Status Endpoint for Per-Server Metrics (PID/RAM/CPU)
    res = requests.get("http://127.0.0.1:5001/status", timeout=5)
    data = res.json()
    
    # Check Global History Buffer
    history = data.get("history", [])
    if len(history) > 0:
        print(f"✅ History Buffer Active: {len(history)} snapshots captured.")
    else:
        print("❌ History Buffer Missing.")
        sys.exit(1)

    # Check Absolute Storage Data
    metrics = data.get("metrics", {})
    if metrics.get("disk_total") and metrics.get("ram_total"):
         print(f"✅ Absolute Storage Data: {metrics['disk_used']}/{metrics['disk_total']} bytes.")
    else:
         print("❌ Absolute Storage Data Missing.")
         sys.exit(1)

    # Check Per-Server Granularity
    servers = data.get("servers", [])
    found_detailed = False
    for s in servers:
        m = s.get("metrics", {})
        if m.get("pid"):
            print(f"✅ Server '{s['name']}' has PID {m['pid']} | CPU: {m['cpu']}% | RAM: {m['ram']} bytes.")
            found_detailed = True
            break
            
    if not found_detailed:
        print("⚠️ Warning: No active servers found to verify per-PID metrics. Start a server to fully verify.")
    
except Exception as e:
    print(f"❌ Verification Failed: {e}")
    sys.exit(1)
