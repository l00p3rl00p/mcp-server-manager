from pathlib import Path

evidence_path = Path('/Users/almowplay/Developer/Github/mcp-creater-manager/EVIDENCE.md')
content = evidence_path.read_text()

update_text = """
### Unit 20: High-Fidelity Command Timeline & Output Capture ✅
- **Date**: 2026-02-18
- **Status**: ✅ COMPLETE - Command lifecycle is now fully transparent.
- **Evidence**: `gui_bridge.py` now uses `NexusSessionLogger` for every execution; `App.tsx` Terminal tab renders full `stdout/stderr` metadata in high-density pre-blocks.
- **Validation**: Running a command in "Operations" now immediately populates the "Terminal" timeline with truth, including the exact output and status.
"""

content += update_text
evidence_path.write_text(content)
print("EVIDENCE.md Updated with Unit 20.")
