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

function showInlineNotice(message, level = 'error') {
    let el = document.getElementById('nexus-inline-notice');
    if (!el) {
        el = document.createElement('div');
        el.id = 'nexus-inline-notice';
        el.style.position = 'fixed';
        el.style.right = '16px';
        el.style.bottom = '16px';
        el.style.maxWidth = '520px';
        el.style.padding = '12px 14px';
        el.style.borderRadius = '10px';
        el.style.background = 'rgba(20, 20, 24, 0.92)';
        el.style.border = '1px solid rgba(255,255,255,0.12)';
        el.style.color = '#fff';
        el.style.fontFamily = 'ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial';
        el.style.fontSize = '13px';
        el.style.lineHeight = '1.3';
        el.style.zIndex = '9999';
        el.style.display = 'none';
        document.body.appendChild(el);
    }

    el.textContent = message;
    el.style.display = 'block';
    el.style.boxShadow = level === 'error' ? '0 12px 30px rgba(255, 80, 80, 0.25)' : '0 12px 30px rgba(0, 160, 255, 0.18)';
    clearTimeout(el._hideTimer);
    el._hideTimer = setTimeout(() => {
        el.style.display = 'none';
    }, 5500);
}

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
            showInlineNotice(`Failed: ${data.message || 'Unknown error'}`, 'error');
        }
    } catch (e) {
        checkbox.checked = !originalState;
        showInlineNotice(`Connection failed: ${e.message}`, 'error');
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
    els.wizardLogs.textContent = '';
    {
        const line = document.createElement('div');
        line.textContent = '> Initializing workforce nexus...';
        els.wizardLogs.appendChild(line);
    }
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
    els.wizardLogs.textContent = '';
    lines.forEach(l => {
        if (l.includes('JSON_LOG:')) {
            let entry;
            try {
                entry = JSON.parse(l.split('JSON_LOG:')[1]);
            } catch (e) {
                entry = { event: 'log', message: l };
            }
            const row = document.createElement('div');
            const tag = document.createElement('span');
            tag.className = 'event-tag';
            tag.textContent = String(entry.event || 'log').toUpperCase();
            row.appendChild(tag);
            row.appendChild(document.createTextNode(' ' + String(entry.message || '')));
            els.wizardLogs.appendChild(row);
            els.wizardStatus.textContent = String(entry.message || '');
            if (entry.event.includes('complete')) {
                els.wizardProgress.style.width = '100%';
                els.wizardDoneBtn.style.display = 'block';
            }
        } else {
            const row = document.createElement('div');
            row.textContent = String(l);
            els.wizardLogs.appendChild(row);
        }
    });
    els.wizardLogs.scrollTop = els.wizardLogs.scrollHeight;
}

// --- Rendering ---
function renderHealth() {
    if (!els.healthMetrics || !state.health) return;
    els.healthMetrics.textContent = '';
    (state.health.checks || []).forEach(c => {
        const item = document.createElement('div');
        item.className = 'metric-item';

        const val = document.createElement('span');
        val.className = 'metric-val';
        val.textContent = c.status === 'ok' ? '✅' : '❌';
        item.appendChild(val);

        const label = document.createElement('span');
        label.className = 'metric-label';
        label.textContent = String(c.name || '');
        item.appendChild(label);

        const msg = document.createElement('div');
        msg.style.fontSize = '0.75rem';
        msg.style.color = 'var(--text-secondary)';
        msg.textContent = String(c.message || '');
        item.appendChild(msg);

        els.healthMetrics.appendChild(item);
    });
}

function renderInventory() {
    if (!els.inventoryTableBody) return;
    els.inventoryCount.textContent = `${state.inventory.length} Network Nodes`;

    els.inventoryTableBody.textContent = '';
    (state.inventory || []).forEach(e => {
        const serverInConfig = state.configState.mcpServers[e.id];
        const isEnabled = serverInConfig ? !serverInConfig.disabled : true;
        const hasToggle = !!serverInConfig;

        const tr = document.createElement('tr');

        const tdName = document.createElement('td');
        const strong = document.createElement('strong');
        strong.textContent = String(e.name || e.id || '');
        tdName.appendChild(strong);
        tr.appendChild(tdName);

        const tdStatus = document.createElement('td');
        const badge = document.createElement('span');
        badge.className = `status-badge ${isEnabled ? 'status-ok' : 'status-warn'}`;
        badge.textContent = isEnabled ? 'Active' : 'Disabled';
        tdStatus.appendChild(badge);
        tr.appendChild(tdStatus);

        const tdToggle = document.createElement('td');
        if (hasToggle) {
            const label = document.createElement('label');
            label.className = 'switch';
            const input = document.createElement('input');
            input.type = 'checkbox';
            input.checked = !!isEnabled;
            input.addEventListener('change', () => toggleServer(String(e.id || ''), input));
            const slider = document.createElement('span');
            slider.className = 'slider';
            label.appendChild(input);
            label.appendChild(slider);
            tdToggle.appendChild(label);
        } else {
            const ext = document.createElement('span');
            ext.className = 'sub-text';
            ext.textContent = 'External';
            tdToggle.appendChild(ext);
        }
        tr.appendChild(tdToggle);

        const tdPath = document.createElement('td');
        tdPath.className = 'sub-text';
        tdPath.textContent = String(e.path || '');
        tr.appendChild(tdPath);

        const tdManage = document.createElement('td');
        const btn = document.createElement('button');
        btn.className = 'btn secondary';
        btn.style.padding = '4px 8px';
        btn.style.fontSize = '0.8rem';
        btn.textContent = 'Update';
        btn.addEventListener('click', () => triggerAction('update', { path: String(e.path || '') }));
        tdManage.appendChild(btn);
        tr.appendChild(tdManage);

        els.inventoryTableBody.appendChild(tr);
    });
}

function renderLogs() {
    if (!els.logViewer) return;
    els.logViewer.textContent = '';
    (state.logs || []).forEach(l => {
        const row = document.createElement('div');
        row.className = 'log-entry';

        const time = document.createElement('span');
        time.className = 'log-time';
        const ts = l.timestamp ? String(l.timestamp) : '';
        time.textContent = ts.includes(' ') ? ts.split(' ')[1] : ts;
        row.appendChild(time);

        const level = document.createElement('span');
        const lvl = String(l.level || '');
        level.className = `log-level level-${lvl}`;
        level.textContent = lvl;
        row.appendChild(level);

        const msg = document.createElement('span');
        msg.textContent = String(l.message || '');
        row.appendChild(msg);

        els.logViewer.appendChild(row);
    });
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
