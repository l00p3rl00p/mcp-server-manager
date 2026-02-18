import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any

class NexusSessionLogger:
    """
    Standardized logger for human-readable command timelines and agent 'thinking' states.
    Writes to ~/.mcpinv/session.jsonl with size-based rotation.
    """
    
    def __init__(self, log_name: str = "session.jsonl", max_size_mb: int = 5):
        self.log_path = Path.home() / ".mcpinv" / log_name
        self.max_size = max_size_mb * 1024 * 1024
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
    def _rotate_if_needed(self):
        if self.log_path.exists() and self.log_path.stat().st_size > self.max_size:
            backup = self.log_path.with_suffix(".jsonl.old")
            if backup.exists():
                backup.unlink()
            self.log_path.rename(backup)

    def log(self, level: str, message: str, suggestion: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        Log an entry to the session timeline.
        Levels: INFO, THINKING, ERROR, COMMAND
        """
        self._rotate_if_needed()
        
        entry = {
            "timestamp": time.time(),
            "iso": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "level": level.upper(),
            "message": message,
            "suggestion": suggestion,
            "metadata": metadata or {}
        }
        
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def log_thinking(self, state: str, reason: Optional[str] = None):
        """Log agent's internal reasoning posture."""
        self.log("THINKING", state, suggestion=reason)

    def log_command(self, cmd: str, status: str, result: Optional[str] = None):
        """Log a system command execution."""
        self.log("COMMAND", f"Executed: {cmd}", suggestion=f"Status: {status}", metadata={"raw_result": result})

if __name__ == "__main__":
    # Test execution
    logger = NexusSessionLogger()
    logger.log_thinking("Normal Operation", "System initialized and waiting for user input.")
    logger.log_command("ls -la", "SUCCESS")
    print(f"✅ Test logs written to {logger.log_path}")
