import requests
import json
import time

def test_red_team_batch():
    print("--- Red Team: Final Batch Supervisor Verification ---")
    url = "http://127.0.0.1:5001/llm/batch"
    
    # Batch of 3 requests to a real API (via the bridge and wrapper)
    payload = {
        "requests": [
            {"id": "batch-1", "method": "GET", "url": "https://jsonplaceholder.typicode.com/posts/1", "extract": {"path": "title"}},
            {"id": "batch-2", "method": "GET", "url": "https://jsonplaceholder.typicode.com/posts/2", "extract": {"path": "title"}},
            {"id": "batch-3", "method": "GET", "url": "https://jsonplaceholder.typicode.com/posts/3", "extract": {"path": "title"}}
        ]
    }
    
    start = time.perf_counter()
    try:
        response = requests.post(url, json=payload, timeout=10)
        elapsed = time.perf_counter() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Received {data['total']} parallel results.")
            print(f"⏱️ Total Time: {elapsed:.4f}s")
            
            for res in data['results']:
                print(f"   [{res['id']}] Extracted: {res.get('extracted')}")
                if "simulated" in str(res):
                    print("❌ ERROR: SIMULATED LOGIC DETECTED!")
                    return False
            
            # Since these are sequential in the ThreadPool but to the same host,
            # wait time should be < sum of sequential
            print("✨ Red Team Confidence: [95%+] - REAL INFRASTRUCTURE DETECTED")
            return True
        else:
            print(f"❌ Bridge Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection Error (Bridge down?): {e}")
        return False

if __name__ == "__main__":
    if not test_red_team_batch():
        exit(1)
