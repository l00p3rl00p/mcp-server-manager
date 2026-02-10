README.md
# Local MCP-Server Discovery + Inventory (mcpinv)

This project implements a **scan-wide / accept-strict** workflow for managing MCP servers installed anywhere on your machine.

## What it does

- Scans your machine (within configured roots) for candidate folders using broad triggers (e.g., `.env`, compose, Dockerfile).
- Applies a strict **MCP Gate**:
  - **Confirmed** → auto-added to inventory
  - **Review** → shown as candidates (operator can add)
  - **Rejected** → ignored (prevents noise)
- Produces a curated, human-editable inventory file: `~/.mcpinv/inventory.yaml`
- Provides a running snapshot (Docker + MCP-ish processes) for heartbeat visibility.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

Configure scan roots
mcpinv config --show
mcpinv config --add-root ~/SomewhereElse
mcpinv config --deep 1

Run a scan
mcpinv scan
mcpinv scan --show-review

Add something scan didn’t detect
mcpinv add --name browser-agent --path "/Users/albert/Code/browser-agent"


If it’s compose-driven:

mcpinv add --name browser-agent --path "/Users/albert/Code/browser-agent" --compose docker-compose.yml --service mcp

Inventory

Stored at:

~/.mcpinv/inventory.yaml

You can edit it by hand. The CLI treats it as source of truth.

Running heartbeat signals
mcpinv running


This is best-effort and intentionally not used as “installed truth”; it’s for the dashboard heartbeat concept.

Recommended ultra-light convention (optional)

If you want near-perfect discovery without central registries, drop this file in any MCP folder:

mcp.server.json

{ "name": "browser-agent", "transport": "http" }


That single file becomes a strong MCP signal and auto-accepts cleanly.


---

# `User_outcomes.md`
```md
# User Outcomes — Local MCP-Server Discovery + Inventory

As a user, I want:

1. **Heartbeat visibility**
   - I can see what MCP servers are likely running right now (Docker/process signals).

2. **Curated inventory**
   - I can keep an authoritative list of my MCP servers, even if they’re installed anywhere.

3. **Low-noise scanning**
   - I can press Scan and trust that it won’t flood my inventory with random `.env` folders.

4. **Operator control**
   - If Scan doesn’t find something, I can add it manually to the inventory.

5. **Explainability**
   - For anything the system detects, I can see *why* it believes it’s MCP (evidence).

6. **Extensibility**
   - I can add optional conventions (like `mcp.server.json` or `.env` marker vars) to improve accuracy without changing my overall install pattern.

   ###############################
   
   # This shows the awalk through of  of the MCP server manager Execution 

## 1️⃣ Two-phase pipeline: *Scan → Gate → Accept*

**Phase A — Scan (wide net)**
Look for any folders that *might* be MCP-ish:

Signals to scan for:

* `.env` / `.env.*`
* `docker-compose.yml` / `compose.yaml`
* `Dockerfile`
* `package.json`
* `pyproject.toml`
* README mentions MCP / modelcontextprotocol

This phase finds **candidates** only. Nothing gets added yet.

---

## 2️⃣ MCP Gate: reject non-standard by default

Create a **hard gate**: a candidate must pass at least **one strong MCP signal** to be accepted automatically.

### Strong MCP signals (auto-accept)

Any **one** of these:

* `package.json` includes `@modelcontextprotocol/*`
* Code contains `modelcontextprotocol` import / reference
* MCP manifest present (`mcp.json`, `mcp.server.json`, etc.)
* Docker labels like `io.mcp.*`
* Service name or image name contains `mcp` **and** exposes a tool/resource endpoint you recognize

If **none** of these are true → **reject by default**.

### Medium signals (flag for review, don’t auto-add)

* `.env` present + Dockerfile present
* Exposes a port commonly used by your MCPs
* README says “MCP” but code doesn’t clearly reference SDK

These go into a **“Review” bucket** in the GUI:

> “Found possible MCP-like services. Review to add.”

### Weak signals (auto-reject)

* `.env` only
* Generic Docker services (databases, redis, etc.)
* Node/Python apps with no MCP references
  These never show up in inventory.

---

## 3️⃣ Reject logic (what gets filtered out hard)

Hard rejects should include:

* Folders with `.env` but **no server runtime** (no Dockerfile, no compose, no start script)
* Docker services exposing ports that are clearly infra (postgres, redis, qdrant, etc.)
* Node apps with only frontend dependencies
* Anything under excluded paths (`node_modules`, `.git`, caches, etc.)

This keeps the GUI clean and prevents the “1000 false MCPs” problem.

---

## 4️⃣ Inventory states (so the UI stays honest)

When scan runs, classify results:

* **Confirmed MCP** → auto-add to inventory
* **Likely MCP** → show in “Review” panel with one-click Add
* **Rejected** → never shown again unless user changes scan rules

Inventory entries get a `confidence` field:

* `confirmed`
* `manual`
* `likely` (if user accepted a medium-confidence one)

---

## 5️⃣ Let the user override the gate (but make it explicit)

In the GUI:

* “Add manually” ignores the gate
* But mark confidence as `manual`
* Display a small badge: “Manually added (not detected as MCP)”

That preserves operator control without polluting auto-discovery.

---

## 6️⃣ Simple MCP signature you can standardize on (tiny but powerful)

If you ever want discovery to be near-perfect, define one optional file:

**`mcp.server.json`**

```json
{
  "name": "browser-agent",
  "transport": "http"
}
```

Then your gate becomes trivial:

* If this file exists → **Confirmed MCP**
* If not → must pass SDK/code signal

This is low ceremony and doesn’t require central registries.

---

## 7️⃣ UX detail that makes this feel “right”

When scan finishes:

* Show:

  * “3 MCP servers added”
  * “2 candidates need review”
  * “47 folders ignored (non-MCP)”

This builds trust that the system is being selective, not noisy.

---

## The principle you’re encoding (and it’s solid)

> **Scan is permissive. Acceptance is strict.**
> **Inventory is curated, not inferred.**

That’s exactly how you avoid tool-sprawl becoming chaos.
