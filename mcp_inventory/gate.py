from __future__ import annotations
from .models import Candidate, GateDecision

# Gate philosophy:
# - Scan wide (many triggers)
# - Accept strict (must have a "strong MCP signal")
# - Otherwise: review (medium) or reject (weak)

STRONG_KINDS = {
    "manifest:mcp.server.json",
    "manifest:mcp.json",
    "dep:@modelcontextprotocol",
    "code:modelcontextprotocol",
    "docker:label:io.mcp",
}

MEDIUM_KINDS = {
    "readme:mentions:mcp",
    "compose:service:contains:mcp",
    "env:llm_keys",
    "docker:image:contains:mcp",
}

WEAK_ONLY_KINDS = {
    "trigger:.env_only",
}

def decide(candidate: Candidate) -> GateDecision:
    kinds = {e.kind for e in candidate.evidence}

    # Strong => auto-accept
    if kinds & STRONG_KINDS:
        return GateDecision(
            accept=True,
            bucket="confirmed",
            reason="Strong MCP signal present."
        )

    # Medium => review (do not auto-add unless user clicks)
    if kinds & MEDIUM_KINDS:
        return GateDecision(
            accept=False,
            bucket="review",
            reason="Medium signals only; requires operator confirmation."
        )

    # Weak-only => reject silently
    if kinds <= WEAK_ONLY_KINDS or not kinds:
        return GateDecision(
            accept=False,
            bucket="rejected",
            reason="Insufficient MCP signals; rejected to avoid noise."
        )

    # Default reject
    return GateDecision(
        accept=False,
        bucket="rejected",
        reason="No qualifying MCP signals."
    )
