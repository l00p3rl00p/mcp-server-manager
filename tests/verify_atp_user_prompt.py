from atp_sandbox import ATPSandbox
import json

def test_user_validation_prompt():
    print("--- ATP User Validation Prompt Test ---")
    sb = ATPSandbox()
    
    # The code from the user's prompt
    code = """
def count_tokens_rough(text: str) -> int:
    \"\"\"Approximates tokens as len(text)//4\"\"\"
    return len(text) // 4

sample = "The quick brown fox jumps over the lazy dog"
tokens = count_tokens_rough(sample)
print(f"Tokens: {tokens}")

# Capture for ATP result
result = {"token_count": tokens, "sample_length": len(sample)}
"""
    
    print("Executing User Logic in Sandbox...")
    response = sb.execute(code)
    
    if response.get("success"):
        print(f"✅ Execution Success!")
        print(f"📊 Logs: {response.get('logs').strip()}")
        print(f"📦 Result: {json.dumps(response.get('result'), indent=2)}")
        
        # Validation checks
        res = response.get("result")
        if res and res.get("token_count") == 43 // 4: # "The quick brown fox jumps over the lazy dog" length is 43
            print("\n✨ ATP VALIDATION: [PASSED]")
            return True
    else:
        print(f"❌ Sandbox Error: {response.get('error')}")
    
    return False

if __name__ == "__main__":
    if test_user_validation_prompt():
        print("Outcome: The whole loop is VERIFIED working for functional Python snippets.")
    else:
        exit(1)
