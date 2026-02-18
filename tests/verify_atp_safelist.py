#!/usr/bin/env python3
"""
Verification Script for ATP Safe List & Shell Safety.
Ensures that commands are correctly categorized and that forbidden patterns (clobber force) are flagged.
"""

import sys
import re

# ATP Safe List Tiers
TIER_1_GREEN = ["echo", "pwd", "whoami", "uptime", "free", "top", "ps", "id", "groups", "hostname", "uname", "df"]
TIER_2_YELLOW = ["ls", "type", "help", "alias", "cat", "grep"]
FORBIDDEN_PATTERNS = [r">\s*\|", r">\|"]  # Catch >| and > |

def categorize_command(command_str):
    """Categorizes a command string based on the ATP Safe List."""
    
    # 1. Check for Forbidden Patterns (Black Tier)
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, command_str):
            return "BLACK (FORBIDDEN)"

    # Tokenize (simplistic splitting for verification)
    tokens = command_str.strip().split()
    if not tokens:
        return "EMPTY"
    
    base_cmd = tokens[0]

    # 2. Check Tiers
    if base_cmd in TIER_1_GREEN:
        return "GREEN (SAFE)"
    elif base_cmd in TIER_2_YELLOW:
        return "YELLOW (STANDARD ALLOWED)"
    else:
        return "UNKNOWN (UNCLASSIFIED)"

def run_tests():
    print("🛡️  Verifying ATP Safe List Logic (Corrected)...\n")
    
    test_cases = [
        ("echo 'Hello'", "GREEN (SAFE)"),
        ("pwd", "GREEN (SAFE)"),
        ("ls -la", "YELLOW (STANDARD ALLOWED)"),
        ("cat file.txt", "YELLOW (STANDARD ALLOWED)"),
        ("grep 'foo' file.txt", "YELLOW (STANDARD ALLOWED)"),
        ("echo 'data' >| file.txt", "BLACK (FORBIDDEN)"),
        ("cat file | grep foo >| output", "BLACK (FORBIDDEN)"),
        ("rm -rf /", "UNKNOWN (UNCLASSIFIED)")
    ]

    failed = False


    for cmd, expected in test_cases:
        result = categorize_command(cmd)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result != expected:
            failed = True
        print(f"[{status}] Cmd: '{cmd}' -> Got: {result} (Expected: {expected})")

    print("\n" + "="*40)
    if failed:
        print("❌ Verification FAILED: Logic errors detected.")
        sys.exit(1)
    else:
        print("✅ Verification PASSED: Safe List logic is sound.")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
