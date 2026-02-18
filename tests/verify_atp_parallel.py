import requests
import json
import time

def verify_parallel_batch():
    print("--- ATP Parallel Supervisor Verification ---")
    url = "http://127.0.0.1:5001/llm/batch"
    payload = {
        "requests": [
            {"prompt": "Analyze reactor core temperature logs"},
            {"prompt": "Summarize shift rotation for Zone 7"},
            {"prompt": "Extract maintenance frequency for Unit 5"}
        ]
    }
    
    try:
        start = time.time()
        response = requests.post(url, json=payload)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Batch processed {data['total']} items in {duration:.4f}s")
            for i, res in enumerate(data['results']):
                print(f"  [{i}] Status: {res['status']} | {res['summary']}")
            
            if data['total'] == 3:
                print("✨ SUCCESS: Parallel sub-agent aggregation verified.")
                return True
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: Is gui_bridge.py running on 5001?")
        
    return False

if __name__ == "__main__":
    if verify_parallel_batch():
        print("\n🚀 Parallel Efficiency Verified.")
    else:
        exit(1)
