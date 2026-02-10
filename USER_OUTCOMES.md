the GUI needs to visualize (and the CLI needs to produce). I’d frame it as five health lenses + one new capability and then turn that into contracts the CLI must satisfy.

1.	Application health

Question: “Am I working correctly and as expected?”
GUI shows: current state, last successful run, current mode, current project, last error, quick actions.
CLI must emit: a single status snapshot (machine-readable) with severity levels and timestamps.

Add (so it’s actionable, not just descriptive):
	•	Run identity: app_version, schema_version, host_os, timezone
	•	State model: state (starting/idle/running/degraded/error), since, severity
	•	Last good baseline: last_good_snapshot_id, last_good_at
	•	Quick actions contract: list of actions the GUI can render (each action is a CLI command reference, not UI logic):
	•	action_id, label, command, requires_confirmation, expected_outcome
	•	Provenance: where the snapshot came from (source files / runtime checks), so the GUI can show “why we believe this.”

⸻

	2.	Command execution health

Question: “Are my commands executing as expected; if not, can a human understand why?”
GUI shows: a timeline of commands with: command name, args, start/end, exit code, stderr summary, and “what to do next.”
CLI must emit: per-command execution records with:
	•	command_id, command_name, args_redacted, started_at, ended_at
	•	exit_code, outcome (success/fail/partial)
	•	error_class (config/auth/network/validation/runtime/unknown)
	•	human_hint (short, specific)

Add (so recovery + audit become first-class):
	•	Correlation: session_id, project_id, parent_command_id (for chained commands)
	•	Artifacts linkage: list of artifact_ids produced/consumed by the command
	•	Retry semantics: retryable (true/false) + retry_hint
	•	Structured stderr summary: error_summary (1–2 lines) separate from raw logs
	•	Deterministic replay: a replay_command string the user can copy/paste (still redacted)
	•	Exit taxonomy: failure_stage (preflight/execution/postprocess/cleanup/unknown)

⸻

	3.	I/O observability

Question: “Are my inputs and outputs being captured, and what do those look like inside the machine?”
GUI shows: inputs/outputs as artifacts: files, payload sizes, destinations, and links to open them.
CLI must emit: artifact records with:
	•	artifact_id, type (prompt, response, file, cache, export, etc.)
	•	path (or URI), size, created_at
	•	optional preview (small safe snippet), and sensitivity flag

Add (so it’s navigable and safe):
	•	Direction: direction (input/output/internal)
	•	Ownership: produced_by_command_id and optional consumed_by_command_ids[]
	•	Integrity: hash (optional), mime_type, encoding
	•	Retention: ttl / retention_policy and can_delete
	•	Safety: sensitivity (public/internal/secret) + redaction_applied (true/false)
	•	Open actions: open_with hints (default viewer, terminal, editor) without the GUI guessing

⸻

	4.	Unified logging (GUI-readable, outside the codebase)

Requirement: logs live in a known, unified location the GUI reads, not in repo folders.
Contract: pick a stable “app data” directory strategy:
	•	macOS: ~/Library/Application Support/<AppName>/
	•	Linux: ~/.local/share/<AppName>/
	•	Windows: %AppData%\<AppName>\

Inside it, keep:
	•	/logs/ (rotating logs)
	•	/state/ (status snapshots, session registry)
	•	/artifacts/ (outputs, exports, cached previews)
	•	/config/ (per-project + per-user config)

GUI only reads these; it doesn’t invent truths.

Add (so it’s operationally stable):
	•	Log formats:
	•	human log: line-oriented text
	•	machine log: JSONL with timestamp, severity, component, event, fields
	•	Rotation + retention: max size, max files, max age (and the CLI reports current policy)
	•	Index pointers: a lightweight state/index.json so the GUI can find “latest snapshot”, “current session”, “last command”, etc. without scanning directories
	•	Atomic writes: snapshots/log records written atomically (temp + rename) to avoid partial reads
	•	Multi-project separation: a projects/<project_id>/... sub-structure under /state/ and /artifacts/ so multiple projects don’t collide
	•	Redaction boundary: secrets never appear in GUI-readable logs; redaction happens in the CLI before writing

	5.	Inventory and discovery health
Question: “What MCP servers exist on this machine, which are running, and can I control them safely?”
GUI shows: inventory table with confidence + evidence, running state, ports, root path, last-seen, plus Start/Stop only when controllable. Scan results split into Confirmed / Review / Rejected.
CLI must emit:

	•	inventory.list → authoritative inventory entries
	•	inventory.scan → candidates + evidence + gate decision
	•	inventory.upsert / inventory.remove → curated updates
	•	runtime.snapshot → observed running signals (docker/process/ports)
	•	inventory.reconcile → “running but not inventoried”, “inventoried but missing”, conflicts

Data contract (per entry):
	•	id, name, path, confidence(confirmed/likely/manual), status(running/stopped/broken/orphan/unknown)
	•	run.kind(compose/docker/local/unknown) + enough fields to control it when possible
	•	ports[], env_files[], transport, tags[], notes
	•	evidence[] (kind/detail/weight)
	•	added_at, last_seen

	6.	Configuration integrity and secrets readiness
Question: “Do I have what I need to run—without guessing—and are secrets handled safely?”
GUI shows: a “requirements” panel: missing keys, invalid values, file not found, permission issues; plus clear fix actions (open config, open terminal, run injector).
CLI must emit:

	•	config.check → structured findings with severity
	•	config.locations → where config is loaded from (user/project/system)
	•	secrets.report → presence-only (never values), with source (env/keychain/file) and scope
	•	fix.suggest → safe, explicit next steps (not auto-fix unless user triggers)

Contract fields:
	•	finding_id, severity(info/warn/error), category(config/auth/fs/permission), message, path_hint, fix_hint

	7.	Session + project context health
Question: “What ‘project’ am I operating on, what session am I in, and what state will carry forward?”
GUI shows: current project, active profile, session id, last activity, and a “switch project” control.
CLI must emit:

	•	context.current → {project_id, project_root, profile, session_id, mode}
	•	context.list_projects → known projects + last used
	•	context.set → explicit switch with audit record

	8.	Performance and resource health
Question: “Is slowness due to my machine, network, provider limits, or my configuration?”
GUI shows: latency breakdown (local compute vs network vs provider), CPU/mem, cache hit rate, queue depth, recent spikes.
CLI must emit:

	•	metrics.snapshot → key counters/timers
	•	metrics.timeseries (optional) → last N minutes
	•	rate_limits / provider_status (best-effort)
	•	per-command timing blocks (already aligned to your Command execution health)

	9.	Update / drift health
Question: “What changed since yesterday—and is that why something broke?”
GUI shows: “since last good run” changes: config diffs (redacted), dependency changes, MCP inventory changes, version changes.
CLI must emit:

	•	changes.since → summarized deltas from stored snapshots
	•	snapshot.save → captures a “known good” baseline
	•	version.report → app version, plugin versions, schema versions

	10.	New capability: guided recovery (the “what do I do next?” layer)
Question: “Given what’s broken, what’s the shortest path to green?”
GUI shows: a ranked set of actions, each with: impact, risk, and exact command preview.
CLI must emit:

	•	recovery.plan → ordered steps derived from findings
	•	each step includes why, command, expected_result, rollback, and requires_confirmation

⸻

The unifying rule (keeps the GUI honest)

For every lens above, the GUI only renders what the CLI wrote into the unified app-data directory:
	•	/state/ (status snapshots, context, inventory, baselines)
	•	/logs/ (rotating)
	•	/artifacts/ (outputs + previews)
	•	/config/ (resolved config views, redacted)

If the GUI needs something new, it’s a new CLI contract, not GUI logic.

