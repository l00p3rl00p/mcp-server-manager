// app.js

const API_BASE = '/api';

// --- State Management ---
const state = {
    health: null,
    inventory: [],
    logs: []
};

// --- DOM Elements ---
const els = {
    statusBadge: document.getElementById('system-status'),
    healthMetrics: document.getElementById('health-metrics'),
    inventoryTableBody: document.querySelector('#inventory-table tbody'),
    inventoryCount: document.getElementById('inventory-count'),
    logViewer: document.getElementById('log-viewer')
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

// --- Actions ---

async function triggerAction(command) {
    updateSystemStatus(`Running ${command}...`, "status-warn");
    try {
        const res = await fetch(`${API_BASE}/action/${command}`, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            // Refresh data after action
            // specific refreshes based on command
            if (command === 'health') fetchHealth();
            if (command === 'scan') fetchInventory();
            if (command === 'running') fetchHealth(); // running updates runtime snapshot which health checks uses? 
            // actually health check runs running_snapshot internally.

            // Allow some time for file writes if needed, but the server action waits for subprocess.
            setTimeout(() => {
                fetchAll();
            }, 500);

            updateSystemStatus("Ready", "status-ok");
        } else {
            alert(`Command failed:\n${data.stderr}`);
            updateSystemStatus("Error", "status-error");
        }
    } catch (e) {
        console.error("Action trigger failed", e);
        updateSystemStatus("Error", "status-error");
    }
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

        // Determine status style
        // We don't have real-time status in inventory entry unless we correlate with runtime.
        // For now, just show what's in the entry.

        tr.innerHTML = `
            <td><strong>${entry.name || entry.id}</strong></td>
            <td>unknown</td> 
            <td>${entry.confidence}</td>
            <td>${entry.transport || '-'}</td>
            <td style="color: #666; font-size: 0.85rem;">${entry.path || ''}</td>
        `;
        tbody.appendChild(tr);
    });
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
        if (log.event) {
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
