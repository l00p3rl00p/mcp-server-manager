// app.js - Premium Workforce Nexus Dashboard
const API_BASE = '/api';

const state = {
    health: null,
    inventory: [],
    configState: { mcpServers: {} },
    logs: [],
    system: { observer: false, librarian: false, injector: false, activator: false },
    activeTab: 'overview'
};

const els = {
    inventoryTableBody: document.querySelector('#inventory-table tbody'),
    inventoryCount: document.getElementById('inventory-count'),
    healthMetrics: document.getElementById('health-metrics'),
    logViewer: document.getElementById('log-viewer'),
    librarianHealth: document.getElementById('librarian-health'),
    statusObserver: document.getElementById('status-observer'),
    statusLibrarian: document.getElementById('status-librarian'),
    statusInjector: document.getElementById('status-injector'),
    statusActivator: document.getElementById('status-activator'),
    tabs: Array.from(document.querySelectorAll('.tab')),
    panels: Array.from(document.querySelectorAll('[data-tab-panel]')),
    wizard: document.getElementById('action-wizard'),
    wizardLogs: document.getElementById('wizard-logs'),
    wizardStatus: document.getElementById('wizard-status'),
    wizardProgress: document.getElementById('wizard-progress'),
    wizardDoneBtn: document.getElementById('wizard-done-btn'),
    wizardTitle: document.getElementById('wizard-title')
};

async function fetchFullState() {
    try {
        const res = await fetch(`${API_BASE}/state/full`);
        if (res.ok) {
            const data = await res.json();

            // 1. Config
            state.configState = data.configState || { mcpServers: {} };

            // 2. Health
            state.health = data.health;

            // 3. Inventory
            state.inventory = data.inventory || [];

            // 4. Logs
            state.logs = data.logs || [];

            // 5. System Status
            state.system = data.system || { observer: false, librarian: false, injector: false, activator: false };

            // Render All
            renderInventory();
            renderHealth();
            renderLogs();
            renderNexusStatus();
        }
    } catch (e) {
        console.error("Optimized fetch failed", e);
    }
}

async function fetchAll() {
    // OPTIMIZATION: Zero-Token / Chatty Reduction
    // Replaced 5 parallel calls with 1 aggregated call.
    await fetchFullState();
}

// --- Toggling ---
async function toggleServer(serverName, checkbox) {
    const originalState = checkbox.checked;
    // UI reflects "Enabled" if checked, but API takes "disabled"
    const isDisabled = !checkbox.checked;

    try {
        const res = await fetch(`${API_BASE}/toggle_server`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: serverName, disabled: isDisabled })
        });
        const data = await res.json();
        if (!data.success) {
            checkbox.checked = !originalState;
            alert(`Failed: ${data.message || 'Unknown error'}`);
        }
    } catch (e) {
        checkbox.checked = !originalState;
        alert(`Connection failed: ${e.message}`);
    }
}

// --- Action Wizard ---
function triggerAction(command, body = null) {
    openWizard(command);
    const fetchOpts = { method: 'POST' };
    if (body) {
        fetchOpts.headers = { 'Content-Type': 'application/json' };
        fetchOpts.body = JSON.stringify(body);
    }
    fetch(`${API_BASE}/action/${command}`, fetchOpts)
        .then(r => r.json())
        .then(data => {
            if (data.success && data.action_log_name) {
                startWizardPolling(data.action_log_name);
            } else {
                setWizardError(data.message || "Failed to start process");
            }
        });
}

function openWizard(title) {
    els.wizardTitle.textContent = title.toUpperCase();
    els.wizardStatus.textContent = "Launching Neural Pipeline...";
    els.wizardLogs.innerHTML = '<div>> Initializing workforce nexus...</div>';
    els.wizardProgress.style.width = '10%';
    els.wizardDoneBtn.style.display = 'none';
    els.wizard.style.display = 'flex';
}

function closeWizard() {
    els.wizard.style.display = 'none';
    fetchAll();
}

function startWizardPolling(logName) {
    const timer = setInterval(async () => {
        const res = await fetch(`${API_BASE}/logs/${logName}`);
        const data = await res.json();
        if (data.lines) {
            renderWizardLines(data.lines);
            const isDone = data.lines.some(l => l.includes('update_complete') || l.includes('scan_complete'));
            if (isDone) clearInterval(timer);
        }
    }, 1000);
}

function renderWizardLines(lines) {
    let html = '';
    lines.forEach(l => {
        if (l.includes('JSON_LOG:')) {
            const entry = JSON.parse(l.split('JSON_LOG:')[1]);
            html += `<div><span class="event-tag">${entry.event.toUpperCase()}</span> ${entry.message}</div>`;
            els.wizardStatus.textContent = entry.message;
            if (entry.event.includes('complete')) {
                els.wizardProgress.style.width = '100%';
                els.wizardDoneBtn.style.display = 'block';
            }
        } else {
            html += `<div>${l}</div>`;
        }
    });
    els.wizardLogs.innerHTML = html;
    els.wizardLogs.scrollTop = els.wizardLogs.scrollHeight;
}

// --- Rendering ---
function renderHealth() {
    if (!els.healthMetrics || !state.health) return;
    els.healthMetrics.innerHTML = state.health.checks.map(c => `
        <div class="metric-item">
            <span class="metric-val">${c.status === 'ok' ? '✅' : '❌'}</span>
            <span class="metric-label">${c.name}</span>
            <div style="font-size: 0.75rem; color: var(--text-secondary);">${c.message}</div>
        </div>
    `).join('');
}

function renderInventory() {
    if (!els.inventoryTableBody) return;
    els.inventoryCount.textContent = `${state.inventory.length} Network Nodes`;

    els.inventoryTableBody.innerHTML = state.inventory.map(e => {
        const serverInConfig = state.configState.mcpServers[e.id];
        const isEnabled = serverInConfig ? !serverInConfig.disabled : true;
        const hasToggle = !!serverInConfig;

        return `
            <tr>
                <td><strong>${e.name || e.id}</strong></td>
                <td><span class="status-badge ${isEnabled ? 'status-ok' : 'status-warn'}">${isEnabled ? 'Active' : 'Disabled'}</span></td>
                <td>
                    ${hasToggle ? `
                        <label class="switch">
                            <input type="checkbox" ${isEnabled ? 'checked' : ''} onchange="toggleServer('${e.id}', this)">
                            <span class="slider"></span>
                        </label>
                    ` : '<span class="sub-text">External</span>'}
                </td>
                <td class="sub-text">${e.path}</td>
                <td><button class="btn secondary" style="padding: 4px 8px; font-size: 0.8rem;" onclick="triggerAction('update', {path: '${e.path}'})">Update</button></td>
            </tr>
        `;
    }).join('');
}

function renderLogs() {
    if (!els.logViewer) return;
    els.logViewer.innerHTML = state.logs.map(l => `
        <div class="log-entry">
            <span class="log-time">${l.timestamp ? l.timestamp.split(' ')[1] : ''}</span>
            <span class="log-level level-${l.level}">${l.level}</span>
            <span>${l.message}</span>
        </div>
    `).join('');
}

function renderNexusStatus() {
    const update = (id, active) => {
        const el = document.getElementById(id);
        if (el) el.className = `status-pill ${active ? 'status-green' : 'status-gray'}`;
    };
    update('status-observer', state.system.observer);
    update('status-librarian', state.system.librarian);
    update('status-injector', state.system.injector);
    update('status-activator', state.system.activator);
}

// --- Tab Handling ---
function wireTabs() {
    els.tabs.forEach(t => {
        t.onclick = () => {
            state.activeTab = t.dataset.tab;
            els.tabs.forEach(btn => btn.classList.toggle('active', btn === t));
            els.panels.forEach(p => p.hidden = p.dataset.tabPanel !== state.activeTab);
            document.getElementById('page-title').textContent = t.textContent;
        };
    });
}

document.addEventListener('DOMContentLoaded', () => {
    wireTabs();
    fetchAll();
    setInterval(fetchAll, 5000);
});
