from mcp import SecureMcpLibrary
from atp_sandbox import ATPSandbox
import json

def verify_atp_efficiency():
    print("--- ATP Efficiency Verification (v16) ---")
    lib = SecureMcpLibrary(":memory:") # Use transient DB for testing
    sb = ATPSandbox()
    
    # 1. Populate data
    print("Step 1: Ingesting 10 bulk records...")
    for i in range(10):
        lib.add_link(f"https://github.com/project-{i}", categories=[f"tag-{i}"])
    
    # 2. Simulate Search_Api (Get all records)
    print("Step 2: Simulating API Discovery...")
    all_records = lib.list_links()
    context = {"records": [{"id": r[0], "url": r[1]} for r in all_records]}
    
    # 3. Simulate Agent-Side Processing (The ATP Way)
    # The agent doesn't want to see 10 records. It only wants the one for project-7.
    print("Step 3: Running 'Code over Tools' filtering (Server Side)...")
    code = """
result = [r for r in context['records'] if 'project-7' in r['url']]
"""
    atp_res = sb.execute(code, context)
    
    if atp_res.get("success"):
        filtered = atp_res["result"]
        print(f"✅ Filtered Result: {json.dumps(filtered)}")
        if len(filtered) == 1 and "project-7" in filtered[0]["url"]:
             print("✨ ATP SUCCESS: 10 records reduced to 1 via server-side logic.")
             return True
        else:
             print(f"❌ Filtering failed. Got {len(filtered)} results.")
    else:
        print(f"❌ Sandbox Error: {atp_res.get('error')}")
    
    return False

if __name__ == "__main__":
    if verify_atp_efficiency():
        print("\n📈 Efficiency Report: 90% Context Reduction Verified.")
    else:
        exit(1)
