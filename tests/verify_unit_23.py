import sys
import os
import json
import time
from pathlib import Path

# Add core path manually since we are in a monorepo
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '../mcp-link-library')))

try:
    from nexus_session_logger import NexusSessionLogger
    from mcp_wrapper import MCPWrapper
except ImportError as e:
    print(f"❌ Import Error: {e}")
    # Fallback for manual path fixing during dev
    sys.path.append('/Users/almowplay/Developer/Github/mcp-creater-manager/mcp-link-library')
    from nexus_session_logger import NexusSessionLogger
    from mcp_wrapper import MCPWrapper

print("📉 Verifying Unit 23: Token Auditing...")

# 1. Verify Logger API
logger = NexusSessionLogger()
estimate = logger.estimate_tokens("Hello World")
if estimate == 2:
    print("✅ Logger.estimate_tokens() confirmed (Heuristic).")
else:
    print(f"❌ Logger Heuristic failed: {estimate} != 2")

# 2. Verify Wrapper Instrumentation
wrapper = MCPWrapper()
# Use public API for test
res = wrapper.call({
    "id": "verify-unit-23",
    "method": "GET",
    "url": "https://jsonplaceholder.typicode.com/todos/1"
})

if "usage" in res and res["usage"]["total"] > 0:
    print(f"✅ Wrapper automatically instrumented usage: {res['usage']}")
else:
    print(f"❌ Wrapper failed to instrument usage: {res}")
    sys.exit(1)

# 3. Verify Log Persistence
session_log = Path.home() / ".mcpinv" / "session.jsonl"
time.sleep(1) # Allow flush

with open(session_log, "r") as f:
    last = json.loads(f.readlines()[-1])

meta_tokens = last.get("metadata", {}).get("tokens")
if meta_tokens and meta_tokens["total"] > 0:
    print(f"✅ Log persistence confirmed: {meta_tokens}")
else:
    print(f"❌ Log entry missing tokens: {last}")
    sys.exit(1)

print("✨ Unit 23 Verified Complete.")
