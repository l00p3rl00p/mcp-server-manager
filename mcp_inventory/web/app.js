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
    },
    system: {
        observer: false,
        librarian: false,
        injector: false,
        activator: false
    }
};

const TAB_DEFAULT = 'overview';

// --- DOM Elements ---
const els = {
    statusBadge: document.getElementById('system-status'),
    healthMetrics: document.getElementById('health-metrics'),
    inventoryTableBody: document.querySelector('#inventory-table tbody'),
    inventoryCount: document.getElementById('inventory-count'),
    logViewer: document.getElementById('log-viewer'),
    librarianHealth: document.getElementById('librarian-health'),
    // Wizard components
    wizard: document.getElementById('action-wizard'),
    wizardLogs: document.getElementById('wizard-logs'),
    wizardStatus: document.getElementById('wizard-status'),
    wizardProgress: document.getElementById('wizard-progress'),
    wizardDoneBtn: document.getElementById('wizard-done-btn'),
    wizardTitle: document.getElementById('wizard-title'),
    tabs: Array.from(document.querySelectorAll('.tabbar .tab')),
    panels: Array.from(document.querySelectorAll('[data-tab-panel]')),
    statusObserver: document.getElementById('status-observer'),
    statusLibrarian: document.getElementById('status-librarian'),
    statusInjector: document.getElementById('status-injector'),
    statusActivator: document.getElementById('status-activator'),
    proxyTransport: document.getElementById('proxy-transport'),
    proxyUri: document.getElementById('proxy-uri'),
    proxyConfig: document.getElementById('proxy-config'),
    proxyCommand: document.getElementById('proxy-command'),
    proxyStatus: document.getElementById('proxy-status'),
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

async function fetchSystemStatus() {
    try {
        const res = await fetch(`${API_BASE}/system_status`);
        if (res.ok) {
            const data = await res.json();
            state.system = data;
            renderNexusStatus();
        }
    } catch (e) {
        console.error("Fetch system status failed", e);
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
    // Legacy single-badge support (for errors)
    // We might want to keep it or repurpose it. 
    // For now, let's leave it but focusing on the Nexus Bar.
}

function renderNexusStatus() {
    const updatePill = (id, active) => {
        const el = document.getElementById(id);
        if (!el) return;
        if (active) {
            el.className = 'status-pill status-green';
            el.innerHTML = el.innerHTML.replace('⚪', '🟢').replace('🔴', '🟢'); // visual fix if needed
        } else {
            el.className = 'status-pill status-gray';
        }
    };

    updatePill('status-observer', state.system.observer);
    updatePill('status-librarian', state.system.librarian);
    updatePill('status-injector', state.system.injector);
    updatePill('status-activator', state.system.activator);
}

function setActiveTab(tabId) {
    const desired = tabId || TAB_DEFAULT;
    els.tabs.forEach((btn) => {
        const match = btn.dataset.tab === desired;
        btn.classList.toggle('active', match);
        btn.setAttribute('aria-selected', match ? 'true' : 'false');
    });
    els.panels.forEach((panel) => {
        panel.hidden = panel.dataset.tabPanel !== desired;
    });
    try {
        localStorage.setItem('mcpinv.activeTab', desired);
    } catch {}
    if (desired === 'librarian') {
        renderLibrarianHealth();
    }
}

function resolveInitialTab() {
    const fromHash = (location.hash || '').replace(/^#/, '').trim();
    if (fromHash) return fromHash;
    try {
        return localStorage.getItem('mcpinv.activeTab') || TAB_DEFAULT;
    } catch {
        return TAB_DEFAULT;
    }
}

function renderLibrarianHealth() {
    if (!els.librarianHealth) return;
    const checks = state.health && Array.isArray(state.health.checks) ? state.health.checks : [];
    const libChecks = checks.filter((c) => typeof c.name === 'string' && (c.name === 'librarian' || c.name.startsWith('lib:')));
    if (libChecks.length === 0) {
        els.librarianHealth.innerHTML = '<div class="sub-text">No librarian checks in the health snapshot yet. Run Health Check.</div>';
        return;
    }
    els.librarianHealth.innerHTML = libChecks
        .map((c) => {
            const icon = c.status === 'ok' ? '✅' : c.status === 'error' ? '❌' : '⚠️';
            return `<div class="log-entry"><span class="log-time">${icon}</span><span>${escapeHtml(c.name)}:</span> ${escapeHtml(c.message || '')}</div>`;
        })
        .join('');
}

function escapeHtml(text) {
    return String(text || '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function renderProxyCommand() {
    if (!els.proxyCommand) return;
    const transport = (els.proxyTransport && els.proxyTransport.value) ? els.proxyTransport.value : 'sse';
    const cfg = (els.proxyConfig && els.proxyConfig.value) ? els.proxyConfig.value : './config.json';
    const cmd = `<your-mcp-proxy> --config "${cfg}" --outputTransport ${transport}`;
    els.proxyCommand.textContent = cmd;
}

// Make available for inline onclick handlers
window.renderProxyCommand = renderProxyCommand;

function setProxyStatus(kind, message) {
    if (!els.proxyStatus) return;
    const cls = kind === 'ok' ? 'status-ok' : kind === 'error' ? 'status-error' : 'status-warn';
    els.proxyStatus.className = `status-badge ${cls}`;
    els.proxyStatus.textContent = message;
}

function defaultUriForTransport(t) {
    if (t === 'ws') return 'ws://localhost:3006/message';
    if (t === 'streamableHttp') return 'http://localhost:3006/mcp';
    return 'http://localhost:3006/sse';
}

async function testProxyConnection() {
    const transport = (els.proxyTransport && els.proxyTransport.value) ? els.proxyTransport.value : 'sse';
    const uri = (els.proxyUri && els.proxyUri.value) ? els.proxyUri.value.trim() : '';
    const target = uri || defaultUriForTransport(transport);
    setProxyStatus('warn', `Testing ${transport} @ ${target} ...`);

    const started = Date.now();
    try {
        if (transport === 'ws') {
            await new Promise((resolve, reject) => {
                let done = false;
                const ws = new WebSocket(target);
                const timer = setTimeout(() => {
                    if (done) return;
                    done = true;
                    try { ws.close(); } catch {}
                    reject(new Error('timeout'));
                }, 3000);
                ws.onopen = () => {
                    if (done) return;
                    done = true;
                    clearTimeout(timer);
                    try { ws.close(); } catch {}
                    resolve(true);
                };
                ws.onerror = () => {
                    if (done) return;
                    done = true;
                    clearTimeout(timer);
                    reject(new Error('ws error'));
                };
            });
            setProxyStatus('ok', `Connection: reachable (ws) in ${Date.now() - started}ms`);
            return;
        }

        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 3000);
        try {
            const res = await fetch(target, {
                method: 'GET',
                headers: transport === 'sse' ? { 'Accept': 'text/event-stream' } : {},
                signal: controller.signal
            });
            clearTimeout(timer);
            setProxyStatus('ok', `Connection: reachable (${res.status}) in ${Date.now() - started}ms`);
        } catch (e) {
            clearTimeout(timer);
            throw e;
        }
    } catch (e) {
        const msg = (e && e.name === 'AbortError') ? 'timeout' : (e && e.message) ? e.message : String(e);
        setProxyStatus('error', `Connection: failed (${msg})`);
    }
}

window.testProxyConnection = testProxyConnection;

function wireTabs() {
    els.tabs.forEach((btn) => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            location.hash = `#${tab}`;
            setActiveTab(tab);
        });
    });
    window.addEventListener('hashchange', () => setActiveTab(resolveInitialTab()));
    setActiveTab(resolveInitialTab());
}

function wireStatusShortcuts() {
    if (els.statusObserver) els.statusObserver.addEventListener('click', () => { location.hash = '#overview'; setActiveTab('overview'); });
    if (els.statusLibrarian) els.statusLibrarian.addEventListener('click', () => { location.hash = '#librarian'; setActiveTab('librarian'); });
    if (els.statusInjector) els.statusInjector.addEventListener('click', () => { location.hash = '#overview'; setActiveTab('overview'); });
    if (els.statusActivator) els.statusActivator.addEventListener('click', () => { location.hash = '#overview'; setActiveTab('overview'); });
}

async function fetchAll() {
    await Promise.all([fetchHealth(), fetchInventory(), fetchLogs(), fetchSystemStatus()]);
}

// Tab + UX wiring is initialized on DOMContentLoaded (see bottom of file).

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
        fetchLogs(),
        fetchSystemStatus()
    ]);
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    wireTabs();
    wireStatusShortcuts();

    // Proxy UX: restore persisted settings
    try {
        const t = localStorage.getItem('mcpinv.proxy.transport');
        const u = localStorage.getItem('mcpinv.proxy.uri');
        const c = localStorage.getItem('mcpinv.proxy.config');
        if (els.proxyTransport && t) els.proxyTransport.value = t;
        if (els.proxyConfig && c) els.proxyConfig.value = c;
        if (els.proxyUri) {
            els.proxyUri.value = u || defaultUriForTransport((els.proxyTransport && els.proxyTransport.value) ? els.proxyTransport.value : 'sse');
        }
    } catch {}

    if (els.proxyTransport && els.proxyUri) {
        els.proxyTransport.dataset.prev = els.proxyTransport.value || 'sse';
        els.proxyTransport.addEventListener('change', () => {
            const next = els.proxyTransport.value;
            // If user is on the old default, update to the new default.
            const current = (els.proxyUri.value || '').trim();
            const prev = els.proxyTransport.dataset.prev || 'sse';
            const wasDefault = !current || current === defaultUriForTransport(prev);
            if (!current || wasDefault) {
                els.proxyUri.value = defaultUriForTransport(next);
            }
            els.proxyTransport.dataset.prev = next;
            try { localStorage.setItem('mcpinv.proxy.transport', next); } catch {}
            renderProxyCommand();
        });
    }
    if (els.proxyUri) {
        els.proxyUri.addEventListener('change', () => {
            try { localStorage.setItem('mcpinv.proxy.uri', els.proxyUri.value.trim()); } catch {}
        });
    }
    if (els.proxyConfig) {
        els.proxyConfig.addEventListener('change', () => {
            try { localStorage.setItem('mcpinv.proxy.config', els.proxyConfig.value.trim()); } catch {}
            renderProxyCommand();
        });
    }

    renderProxyCommand();
    setProxyStatus('warn', 'Connection: unknown');
    fetchAll();

    // Poll logs every 5s
    // Poll logs every 5s
    setInterval(() => {
        fetchLogs();
        fetchSystemStatus();
    }, 5000);

    // We could poll status too, to see if actions completed?
});
