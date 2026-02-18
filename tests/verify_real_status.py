
import requests
import json
import os
from pathlib import Path

def main():
    url = "http://127.0.0.1:5001/status"
    print(f"🏥 Checking Nexus Status API: {url}")
    
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print("\n📊 System Status Snapshot:")
            print(json.dumps(data, indent=2))
            
            # Check for core components
            components = ["activator", "observer", "surgeon", "librarian"]
            all_good = True
            for comp in components:
                status = data.get(comp, "missing")
                if status == "online":
                    print(f"✅ {comp.capitalize()}: {status}")
                elif status == "stopped":
                    print(f"⚠️  {comp.capitalize()}: {status} (Expected if not running)")
                else:
                    print(f"❌ {comp.capitalize()}: {status}")
                    all_good = False
            
            if all_good:
                print("\n✅ Verification SUCCESS: Status API is reporting real system state.")
            else:
                print("\n❌ Verification FAIL: One or more components are missing.")
        else:
            print(f"❌ Error: Received status code {resp.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
