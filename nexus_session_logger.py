import os
import json
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any


class NexusSessionLogger:
    """
    Standardized logger for human-readable command timelines and agent 'thinking' states.
    Writes to ~/.mcpinv/session.jsonl with size-based rotation.

    Thread-safe: all file writes are protected by a per-instance Lock so that
    concurrent forge threads and HTTP handlers don't interleave JSONL entries.
    """

    def __init__(self, log_name: str = "session.jsonl", max_size_mb: int = 5):
        self.log_path = Path.home() / ".mcpinv" / log_name
        self.max_size = max_size_mb * 1024 * 1024
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        # Protects file writes from concurrent threads (forge + HTTP handlers)
        self._lock = threading.Lock()

    def _rotate_if_needed(self):
        """Rotate log file when it exceeds max_size to keep disk usage bounded."""
        if self.log_path.exists() and self.log_path.stat().st_size > self.max_size:
            backup = self.log_path.with_suffix(".jsonl.old")
            if backup.exists():
                backup.unlink()
            self.log_path.rename(backup)

    def log(self, level: str, message: str, suggestion: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        Log an entry to the session timeline.
        Levels: INFO, THINKING, ERROR, COMMAND

        Acquires the instance lock before writing so concurrent callers
        from different threads produce valid, non-interleaved JSONL.
        """
        entry = {
            "timestamp": time.time(),
            "iso": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "level": level.upper(),
            "message": message,
            "suggestion": suggestion,
            "metadata": metadata or {}
        }
        # Lock covers both rotation check and write to prevent TOCTOU race
        with self._lock:
            self._rotate_if_needed()
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

    def log_thinking(self, state: str, reason: Optional[str] = None):
        """Log agent's internal reasoning posture."""
        self.log("THINKING", state, suggestion=reason)

    def log_command(self, cmd: str, status: str, result: Optional[str] = None, tokens: Optional[Dict[str, Any]] = None):
        """
        Log a system command execution with optional token usage.
        tokens dict (input/output/total) is written into metadata.usage for cost tracking (v23).
        """
        meta: Dict[str, Any] = {"raw_result": result}
        if tokens:
            meta["usage"] = tokens  # v23: persist token cost in JSONL
        self.log("COMMAND", f"Executed: {cmd}", suggestion=f"Status: {status}", metadata=meta)


if __name__ == "__main__":
    """Smoke test: verify thread-safe logging works end-to-end."""
    logger = NexusSessionLogger()
    logger.log_thinking("Normal Operation", "System initialized and waiting for user input.")
    logger.log_command("ls -la", "SUCCESS")
    print(f"✅ Test logs written to {logger.log_path}")
