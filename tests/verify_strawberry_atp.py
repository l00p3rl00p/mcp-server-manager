import json
import sys
from pathlib import Path

# Add mcp-link-library to path
lib_path = Path("/Users/almowplay/Developer/Github/mcp-creater-manager/mcp-link-library")
sys.path.append(str(lib_path))

try:
    from mcp import SecureMcpLibrary, MCPServer
    from atp_sandbox import ATPSandbox
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def run_strawberry_test():
    print("--- 🍓 ATP 'Strawberry' Real-Logic Test ---")
    
    import random
    
    # 1. Setup Sandbox
    sb = ATPSandbox()
    
    # 2. Randomized Tests
    tests = [
        {
            "name": "Strawberry 'r' Count",
            "sentence": "The strawberry is Ripe and Ready, but are there 3 r's or 4?",
            "context": {"text": "The strawberry is Ripe and Ready, but are there 3 r's or 4?", "char": "r"},
            "code": "result = {'count': context.get('text', '').lower().count(context.get('char', 'r').lower())}",
            "expected": 9
        },
        {
            "name": "Math Evaluation",
            "sentence": "Compute (15 * 3) + 7 - 2",
            "context": {},
            "code": "result = {'count': (15 * 3) + 7 - 2}",
            "expected": 50
        },
        {
            "name": "List Filtering",
            "sentence": "Count even numbers in 1 to 10",
            "context": {"nums": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]},
            "code": "result = {'count': len([x for x in context['nums'] if x % 2 == 0])}",
            "expected": 5
        }
    ]
    test = random.choice(tests)
    print(f"Executing ATP Sandbox with test: '{test['name']}' ({test['sentence']})")
    
    # 3. Execution (Simulating MCP execute_code call)
    exec_res = sb.execute(test["code"], test["context"])
    
    if exec_res["success"] and isinstance(exec_res.get("result"), dict):
        res_data = exec_res["result"]
        print(f"✅ Result: {json.dumps(res_data, indent=2)}")
        
        if res_data and res_data.get("count") == test["expected"]:
            print(f"✨ SUCCESS: ATP Sandbox proved deterministic precision for {test['name']}.")
        else:
            print(f"❌ ERROR: Count mismatch (Got {res_data.get('count')}, expected {test['expected']}).")
    else:
         print(f"❌ Sandbox Error: {exec_res.get('error')}")

if __name__ == "__main__":
    run_strawberry_test()
