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
    
    # 1. Setup Sandbox
    sb = ATPSandbox()
    
    # 2. The Deterministic Protocol (Logic instead of Chat)
    # Goal: Count 'r' in a tricky sentence case-insensitively.
    sentence = "The strawberry is Ripe and Ready, but are there 3 r's or 4?"
    code = """
text = context.get('text', '')
target = context.get('char', 'r')
# Real function: Case-insensitive count
result = {
    "char": target,
    "count": text.lower().count(target.lower()),
    "source": "ATP_DETERMINISTIC_LOGIC"
}
"""
    
    # 3. Execution (Simulating MCP execute_code call)
    print(f"Executing ATP Sandbox with sentence: '{sentence}'")
    exec_res = sb.execute(code, {"text": sentence, "char": "r"})
    
    if exec_res["success"]:
        res_data = exec_res["result"] # The 'result' variable from sandbox
        print(f"✅ Result: {json.dumps(res_data, indent=2)}")
        
        if res_data and res_data.get("count") == 9:
            print("✨ SUCCESS: ATP Sandbox proved deterministic precision (Librarian level).")
        else:
            print(f"❌ ERROR: Count mismatch (Got {res_data['count']}, expected 9).")
    else:
         print(f"❌ Sandbox Error: {exec_res.get('error')}")

if __name__ == "__main__":
    run_strawberry_test()
