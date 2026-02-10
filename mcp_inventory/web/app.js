// app.js

const API_BASE = '/api';

// --- State Management ---
const state = {
    health: null,
    inventory: [],
    logs: [],
    wizard: {
        active: false,
        logName: null,
        timer: null
    }
};

// --- DOM Elements ---
const els = {
    statusBadge: document.getElementById('system-status'),
    healthMetrics: document.getElementById('health-metrics'),
    inventoryTableBody: document.querySelector('#inventory-table tbody'),
    inventoryCount: document.getElementById('inventory-count'),
    logViewer: document.getElementById('log-viewer'),
    // Wizard components
    wizard: document.getElementById('action-wizard'),
    wizardLogs: document.getElementById('wizard-logs'),
    wizardStatus: document.getElementById('wizard-status'),
    wizardProgress: document.getElementById('wizard-progress'),
    wizardDoneBtn: document.getElementById('wizard-done-btn'),
    wizardTitle: document.getElementById('wizard-title')
};

// --- Fetch Data ---

async function fetchHealth() {
    try {
        const res = await fetch(`${API_BASE}/state/health`);
        if (res.ok) {
            const data = await res.json();
            state.health = data;
            renderHealth();
            updateSystemStatus("Connected", "status-ok");
        } else {
            console.warn("Health data not found");
            updateSystemStatus("No Data", "status-warn");
        }
    } catch (e) {
        console.error("Fetch health failed", e);
        updateSystemStatus("Disconnected", "status-error");
    }
}

async function fetchInventory() {
    try {
        const res = await fetch(`${API_BASE}/state/inventory`);
        if (res.ok) {
            const data = await res.json();
            // data.entries is the array
            state.inventory = data.entries || [];
            renderInventory();
        }
    } catch (e) {
        console.error("Fetch inventory failed", e);
    }
}

async function fetchLogs() {
    try {
        const res = await fetch(`${API_BASE}/logs`);
        if (res.ok) {
            const data = await res.json();
            state.logs = data.logs || [];
            renderLogs();
        }
    } catch (e) {
        console.error("Fetch logs failed", e);
    }
}

// --- Action Wizard Core Logic ---

/**
 * Triggers a server action and opens the Wizard overlay for monitoring.
 * This is the main bridge between the UI and the Shesha CLI.
 * 
 * @param {string} command - The command to run (scan, health, update, etc.)
 * @param {Object} body - Optional POST body (e.g., {path: '...'})
 */
async function triggerAction(command, body = null) {
    // 1. Reset and Show Wizard UI immediately for responsiveness
    openWizard(command);

    try {
        const fetchOpts = { method: 'POST' };
        if (body) {
            fetchOpts.headers = { 'Content-Type': 'application/json' };
            fetchOpts.body = JSON.stringify(body);
        }

        // 2. Start the remote process via the API
        const res = await fetch(`${API_BASE}/action/${command}`, fetchOpts);
        const data = await res.json();

        if (data.success && data.action_log_name) {
            // 3. The server returned a log filename for this specific execution.
            // Begin polling this file for incremental updates.
            state.wizard.logName = data.action_log_name;
            startWizardPolling();
        } else {
            setWizardError(data.stderr || "Failed to start process");
        }
    } catch (e) {
        setWizardError(`Connection failed: ${e.message}`);
    }
}

/** Prepares the modal UI for a new action run */
function openWizard(title) {
    state.wizard.active = true;
    els.wizardTitle.textContent = title.toUpperCase();
    els.wizardStatus.textContent = "Launching CLI...";
    els.wizardLogs.innerHTML = '<div style="color: #666">> Initializing workforce pipeline...</div>';
    els.wizardProgress.style.width = '10%';
    els.wizardDoneBtn.style.display = 'none';
    els.wizard.style.display = 'flex';
}

/** Closes the wizard and triggers a full dashboard refresh to show new data */
function closeWizard() {
    state.wizard.active = false;
    if (state.wizard.timer) clearInterval(state.wizard.timer);
    els.wizard.style.display = 'none';
    fetchAll(); // Refresh inventory and status
}

/** Displays a critical error message inside the wizard */
function setWizardError(msg) {
    els.statusBadge.textContent = "Error"; // Update top-bar status too
    els.wizardStatus.textContent = "Operation Failed";
    els.wizardStatus.style.color = "var(--error-color)";
    els.wizardLogs.innerHTML += `<div style="color:var(--error-color); margin-top:10px;">[!] ${msg}</div>`;
    els.wizardDoneBtn.style.display = 'block';
    els.wizardProgress.style.backgroundColor = 'var(--error-color)';
}

/** 
 * Polls the specific action log file every second.
 * This allows the UI to 'tail' the subprocess output in real-time.
 */
function startWizardPolling() {
    if (state.wizard.timer) clearInterval(state.wizard.timer);

    state.wizard.timer = setInterval(async () => {
        if (!state.wizard.active) return;

        try {
            const res = await fetch(`${API_BASE}/logs/${state.wizard.logName}`);
            const data = await res.json();

            if (data.lines) {
                renderWizardLines(data.lines);
            }
        } catch (e) {
            console.error("Wizard poll failed", e);
        }
    }, 1000);
}

/**
 * Parses raw CLI output and structured JSON_LOG markers.
 * Updates progress bar and status message based on lifecycle events.
 */
function renderWizardLines(lines) {
    let html = '';
    let progress = 20;

    lines.forEach(line => {
        // Detect and parse machine-readable markers emitted by install.py --machine
        if (line.includes('JSON_LOG:')) {
            try {
                const jsonPart = line.split('JSON_LOG:')[1];
                const entry = JSON.parse(jsonPart);

                // Map lifecycle events to progress percentages
                if (entry.event === 'update_start') progress = 30;
                if (entry.event === 'git_pull_success') progress = 60;
                if (entry.event === 'deps_refresh') progress = 80;
                if (entry.event === 'update_complete' || entry.event === 'scan_complete') {
                    progress = 100;
                    els.wizardStatus.textContent = "Operation Complete";
                    els.wizardDoneBtn.style.display = 'block';
                }

                // Prettify the structured log for the wizard window
                html += `<div><span class="event-tag">${entry.event.toUpperCase()}</span> ${entry.message}</div>`;
                els.wizardStatus.textContent = entry.message;
            } catch (e) {
                html += `<div style="color:#444">${line}</div>`;
            }
        } else if (line.trim()) {
            // Echo standard stdout/stderr lines
            if (!line.startsWith('---')) { // Skip the command header line
                html += `<div>${line}</div>`;
            }
        }
    });

    els.wizardLogs.innerHTML = html;
    els.wizardLogs.scrollTop = els.wizardLogs.scrollHeight; // Auto-scroll to latest
    els.wizardProgress.style.width = `${progress}%`;
}

async function runHealthCheck() {
    await triggerAction('health');
}

// --- Rendering ---

function updateSystemStatus(text, className) {
    els.statusBadge.textContent = text;
    els.statusBadge.className = `status-badge ${className}`;
}

function renderHealth() {
    els.healthMetrics.innerHTML = '';
    if (!state.health || !state.health.checks) return;

    state.health.checks.forEach(check => {
        const div = document.createElement('div');
        div.className = 'metric-item';

        const icon = check.status === 'ok' ? '✅' : (check.status === 'error' ? '❌' : '⚠️');

        div.innerHTML = `
            <span class="metric-val">${icon}</span>
            <span class="metric-label">${check.name}</span>
            <div style="font-size: 0.75rem; margin-top: 4px; color: #888;">${check.message}</div>
        `;
        els.healthMetrics.appendChild(div);
    });
}

function renderInventory() {
    const tbody = els.inventoryTableBody;
    tbody.innerHTML = '';

    els.inventoryCount.textContent = state.inventory.length;

    if (state.inventory.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color: #666;">No inventory items found. Run a scan.</td></tr>';
        return;
    }

    state.inventory.forEach(entry => {
        const tr = document.createElement('tr');
        if (entry.install_mode === 'managed') {
            tr.classList.add('row-managed');
        }

        const isManaged = entry.install_mode === 'managed';
        const remoteInfo = entry.remote_url ? `<div class="sub-text">${entry.remote_url}</div>` : '';

        const updateBtn = isManaged
            ? `<button class="btn-sm primary" onclick="updateServer('${entry.id}', '${entry.path.replace(/\\/g, '/')}')">Update</button>`
            : '';

        tr.innerHTML = `
            <td>
                <div><strong>${entry.name || entry.id}</strong></div>
                ${isManaged ? '<span class="badge-sm badge-managed">MANAGED</span>' : ''}
            </td>
            <td>${entry.status || 'unknown'}</td> 
            <td>${entry.confidence}</td>
            <td>${entry.transport || '-'}</td>
            <td style="color: #666; font-size: 0.85rem;">
                ${entry.path || ''}
                ${remoteInfo}
            </td>
            <td>${updateBtn}</td>
        `;
        tbody.appendChild(tr);
    });
}

function updateServer(id, path) {
    if (!confirm(`Are you sure you want to update ${id}?\n\nThis will pull the latest code and refresh dependencies.`)) {
        return;
    }
    triggerAction('update', { server_id: id, path: path });
}

function renderLogs() {
    const container = els.logViewer;
    container.innerHTML = '';

    // Reverse to show newest top? or scroll to bottom. 
    // Usually logs are top-down. Let's scroll to bottom.

    state.logs.forEach(log => {
        const div = document.createElement('div');
        div.className = 'log-entry';

        const timeStr = log.timestamp ? log.timestamp.split(' ')[1].split(',')[0] : ''; // Simple time parse
        const levelClass = `level-${log.level}`;

        // Format message - if it has props, show them?
        let msg = log.message;

        // Machine-readable log handling
        if (msg.startsWith("JSON_LOG:")) {
            try {
                const parsed = JSON.parse(msg.substring(9));
                msg = `<span class="event-tag">${parsed.event.toUpperCase()}</span> ${parsed.message}`;
                if (parsed.data && Object.keys(parsed.data).length > 0) {
                    msg += ` <span class="log-msg-json">${JSON.stringify(parsed.data)}</span>`;
                }
                div.classList.add(`event-${parsed.event}`);
            } catch (e) { }
        } else if (log.event) {
            msg = `[${log.event}] ${msg}`;
            // If extra fields
            const extras = { ...log };
            delete extras.timestamp;
            delete extras.level;
            delete extras.message;
            delete extras.logger;
            delete extras.event;

            if (Object.keys(extras).length > 0) {
                msg += ` ${JSON.stringify(extras)}`;
            }
        }

        div.innerHTML = `
            <span class="log-time">${timeStr}</span>
            <span class="log-level ${levelClass}">${log.level}</span>
            <span class="log-msg">${msg}</span>
        `;
        container.appendChild(div);
    });

    container.scrollTop = container.scrollHeight;
}

// --- Init ---

async function fetchAll() {
    await Promise.all([
        fetchHealth(),
        fetchInventory(),
        fetchLogs()
    ]);
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    fetchAll();

    // Poll logs every 5s
    setInterval(fetchLogs, 5000);

    // We could poll status too, to see if actions completed?
});
