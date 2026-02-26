import React, { useState, useEffect, useMemo, useCallback } from 'react';
import Sparkline from './components/Sparkline';
import {
  Activity, ShieldCheck, Settings,
  LayoutDashboard, Search, Cpu, Monitor,
  HardDrive, Globe, AlertTriangle, X, Trash2,
  FileText, Library, Terminal,
  ChevronDown, ChevronUp, CheckCircle2, Info, Copy, Wrench
} from 'lucide-react';

// Types
interface LogEntry {
  timestamp: number;
  iso: string;
  level: string;
  message: string;
  suggestion?: string;
  metadata?: {
    raw_result?: string;
    error?: string;
    tokens?: {
      input: number;
      output: number;
      total: number;
    };
  };
}

interface Notification {
  id: number;
  type: 'success' | 'error' | 'info';
  message: string;
}

/**
 * Single source of truth for the backend URL.
 * Override via VITE_API_URL env var for staging/production deployments.
 * All fetch() calls in this file should use API_BASE — never hardcode localhost directly.
 */
const API_BASE = (import.meta as any).env?.VITE_API_URL || "";

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [logViewer, setLogViewer] = useState<{ serverId: string; data: any } | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<string | null>(null);
  const [metricPanelOpen, setMetricPanelOpen] = useState(false);

  const openMetricPanel = (metric: string) => {
    if (metricPanelOpen && selectedMetric === metric) {
      // Same button clicked — close panel
      setMetricPanelOpen(false);
    } else {
      setSelectedMetric(metric);
      setMetricPanelOpen(true);
    }
  };

  const closeMetricPanel = () => setMetricPanelOpen(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [systemStatus, setSystemStatus] = useState<any>({
    metrics: { cpu: 0, memory: 0, disk: 0, net: { sent: 0, recv: 0 }, ram_used: 0, ram_total: 0, disk_used: 0, disk_total: 0 },
    history: [] as any[],
    pulse: 'green',
    servers: [],
    posture: 'Initializing...'
  });
  const [links, setLinks] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [scanRoots, setScanRoots] = useState<any[]>([]);
  const [watcherStatus, setWatcherStatus] = useState<string>("offline");
  const [healthIssues, setHealthIssues] = useState<any[]>([]);
  const [selectedLogEntry, setSelectedLogEntry] = useState<LogEntry | null>(null);
  const [inventoryHistory, setInventoryHistory] = useState<any[]>([]);
  const [commandCatalog, setCommandCatalog] = useState<any[]>([]);
  const [catalogInputs, setCatalogInputs] = useState<any>({});
  const [quickIndexResource, setQuickIndexResource] = useState<string>('');
  const [librarianLastIndexed, setLibrarianLastIndexed] = useState<{ resource: string; when: number } | null>(null);
  const [serverDrawer, setServerDrawer] = useState<{ serverId: string; mode: 'log' | 'report' | 'inspect' } | null>(null);
  const [serverDrawerData, setServerDrawerData] = useState<Record<string, any>>({});
  const [logBrowserOpen, setLogBrowserOpen] = useState(false);
  const [logBrowserMode, setLogBrowserMode] = useState<'audit' | 'lifecycle'>('audit');
  const [logBrowserServerId, setLogBrowserServerId] = useState<string>('');
  const [logBrowserPayload, setLogBrowserPayload] = useState<string>('');
  const [coreDrawerKey, setCoreDrawerKey] = useState<string | null>(null);
  // GAP-R2 FIX: Drift detection — tracks source vs mirror hash divergence
  const [driftReport, setDriftReport] = useState<{ any_drift: boolean; repair_command: string; repos: any[] } | null>(null);
  const [inventoryView, setInventoryView] = useState<'card' | 'list'>(() => {
    return (localStorage.getItem('nexus_inventory_view') as 'card' | 'list') || 'card';
  });

  useEffect(() => {
    localStorage.setItem('nexus_inventory_view', inventoryView);
  }, [inventoryView]);

  // Forge State
  const [forgeSource, setForgeSource] = useState('');
  const [forgeName, setForgeName] = useState('');
  const [isForging, setIsForging] = useState(false);
  const [forgeResult, setForgeResult] = useState<any>(null);

  // Injection State
  // Injection State
  const [injectTarget, setInjectTarget] = useState<any>(null);
  const [injectionStatus, setInjectionStatus] = useState<any>(null);
  const [targetClient, setTargetClient] = useState('');
  const [availableClients, setAvailableClients] = useState<string[]>([]);
  const [pendingServerAction, setPendingServerAction] = useState<Record<string, string>>({});
  const [pythonInfo, setPythonInfo] = useState<any>(null);
  const [purgeModalOpen, setPurgeModalOpen] = useState(false);
  const [purgeConfirmText, setPurgeConfirmText] = useState("");
  const [purgePreview, setPurgePreview] = useState<{ ok: boolean; stdout: string; stderr: string; raw?: string } | null>(null);
  const [purgePreviewLoading, setPurgePreviewLoading] = useState(false);
  const [purgeOptions, setPurgeOptions] = useState({
    // Default reset: environments only (keep suite installed).
    purge_data: false,
    purge_env: true,
    kill_venv: true,
    // Detach defaults:
    // - managed servers: yes (their envs are being reset)
    // - suite tools: no (keep Commander + suite tools available)
    detach_clients: false,
    detach_managed_servers: true,
    detach_suite_tools: false,
    // PATH cleanup is opt-in (do not surprise users).
    remove_path_block: false,
    remove_wrappers: false,
  });

  type SideConfirmState = {
    title: string;
    details?: string;
    confirmLabel?: string;
    cancelLabel?: string;
    danger?: boolean;
    onConfirm?: () => void | Promise<void>;
  };
  const [sideConfirm, setSideConfirm] = useState<SideConfirmState | null>(null);

  const openConfirmPanel = (next: SideConfirmState) => {
    setSideConfirm({
      cancelLabel: 'Cancel',
      confirmLabel: 'Confirm',
      danger: false,
      ...next,
    });
  };

  const splitCmd = (cmd: string): string[] => {
    const m = cmd.match(/(?:[^\s"]+|"[^"]*")+/g) || [];
    return m.map(x => x.replace(/^"(.*)"$/, '$1')).filter(Boolean);
  };

  const buildInjectionCommand = (s: any, client: string): string | null => {
    const startCmd = (s?.raw?.run?.start_cmd || '').toString();
    if (!startCmd) return null;
    const parts = splitCmd(startCmd);
    if (parts.length < 1) return null;

    const command = parts[0];
    let args = parts.slice(1);

    // If forged inventory uses `python ... mcp_server.py`, make the script path absolute so the client can run it.
    try {
      if (args.length >= 1 && args[0] === 'mcp_server.py' && s?.raw?.path) {
        const base = (s.raw.path || '').toString().replace(/\/+$/, '');
        args = [`${base}/mcp_server.py`, ...args.slice(1)];
      }
    } catch { }

    const q = (x: string) => `"${(x || '').replace(/"/g, '\\"')}"`;
    const argStr = args.map(a => q(a)).join(' ');

    // Deterministic surgeon add: inject exactly what's in inventory (no templates, no guessing).
    return `mcp-surgeon --client ${client} --add --name ${q(s.id)} --command ${q(command)}${args.length ? ` --args ${argStr}` : ''}`;
  };

  // Terminal Filter State
  const [terminalFilter, setTerminalFilter] = useState('');
  const [terminalLevel, setTerminalLevel] = useState('ALL');
  const [expandedLog, setExpandedLog] = useState<number | null>(null);

  // Notifications
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = useCallback((message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, type, message }]);
    setTimeout(() => setNotifications(prev => prev.filter(n => n.id !== id)), 5000);
  }, []);

  const openLastStartLog = async (serverId: string) => {
    try {
      const res = await fetch(API_BASE + `/server/logs/${encodeURIComponent(serverId)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'No logs found');
      setLogViewer({ serverId, data });
    } catch (e: any) {
      addNotification(`Log viewer failed: ${e.message || String(e)}`, 'error');
    }
  };

  const openServerDrawer = async (serverId: string, mode: 'log' | 'report' | 'inspect', serverRaw?: any) => {
    if (serverDrawer?.serverId === serverId && serverDrawer?.mode === mode) {
      setServerDrawer(null);
      return;
    }
    setServerDrawer({ serverId, mode });

    const key = `${serverId}:${mode}`;
    if (mode === 'inspect') {
      setServerDrawerData(prev => ({ ...prev, [key]: serverRaw ?? prev[key] ?? null }));
      return;
    }
    try {
      if (mode === 'log') {
        const res = await fetch(API_BASE + `/server/logs/${encodeURIComponent(serverId)}`);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || 'No logs found');
        setServerDrawerData(prev => ({ ...prev, [key]: data }));
        return;
      }
      if (mode === 'report') {
        const res = await fetch(API_BASE + `/export/report.json?server=${encodeURIComponent(serverId)}`);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || 'Report failed');
        setServerDrawerData(prev => ({ ...prev, [key]: data }));
        return;
      }
    } catch (e: any) {
      addNotification(`Panel failed: ${e.message || String(e)}`, 'error');
      setServerDrawerData(prev => ({ ...prev, [key]: { error: String(e?.message || e) } }));
    }
  };

  const openLogBrowser = async (mode: 'audit' | 'lifecycle', serverId?: string) => {
    setLogBrowserMode(mode);
    const nextServerId = serverId ?? logBrowserServerId ?? '';
    setLogBrowserServerId(nextServerId);
    setLogBrowserOpen(true);
    try {
      if (mode === 'audit') {
        const res = await fetch(API_BASE + `/export/report.json${nextServerId ? `?server=${encodeURIComponent(nextServerId)}` : ''}`);
        const data = await res.json().catch(() => ({}));
        setLogBrowserPayload(JSON.stringify(data, null, 2));
        if (!res.ok) addNotification(data.error || 'Audit report failed.', 'error');
        return;
      }
      if (mode === 'lifecycle') {
        if (!nextServerId) {
          setLogBrowserPayload('Select a server to view lifecycle logs.');
          return;
        }
        const res = await fetch(API_BASE + `/server/logs/${encodeURIComponent(nextServerId)}`);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || 'No logs found');
        const text = ((data?.lines || []) as string[]).join('\n');
        setLogBrowserPayload(text || '(empty log)');
        return;
      }
    } catch (e: any) {
      setLogBrowserPayload(String(e?.message || e));
      addNotification(String(e?.message || e), 'error');
    }
  };

  const fetchData = async () => {
    try {
      const endpoints: [string, (d: any) => void][] = [
        ['logs', setLogs],
        ['status', (d) => d && setSystemStatus(d)],
        ['librarian/links', setLinks],
        ['nexus/projects', setProjects],
        ['librarian/roots', setScanRoots],
        ['librarian/watcher', (d: any) => d?.status && setWatcherStatus(d.status)],
        ['validate', setHealthIssues],
        ['project/history', setInventoryHistory],
        ['nexus/catalog', setCommandCatalog],
        ['forge/last', (d) => d && Object.keys(d).length > 0 && setForgeResult({ ...d, status: 'completed' })],
        ['system/python_info', (d) => d && d.success && setPythonInfo(d)],
        ['system/drift', (d) => d && setDriftReport(d)]
      ];

      await Promise.all(endpoints.map(async ([path, setter]) => {
        try {
          const res = await fetch(`${API_BASE}/${path}`);
          if (res.ok) {
            const data = await res.json();
            if (data !== null) setter(data);
          }
        } catch (e) { }
      }));
    } catch (err) {
      console.error("Fetch failed:", err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  // Drift detection: poll every 60s (slower — file hashing is cheap but no need to hammer)
  useEffect(() => {
    const driftPoll = async () => {
      try {
        const res = await fetch(`${API_BASE}/system/drift`);
        if (res.ok) { const d = await res.json(); setDriftReport(d); }
      } catch { }
    };
    driftPoll();
    const interval = setInterval(driftPoll, 60000);
    return () => clearInterval(interval);
  }, []);


  // AUTO_REFRESH_LOG_BROWSER: when the Log Browser is open, poll the selected view.
  useEffect(() => {
    if (!logBrowserOpen) return;
    openLogBrowser(logBrowserMode, logBrowserServerId);
    const interval = setInterval(() => {
      openLogBrowser(logBrowserMode, logBrowserServerId);
    }, 2000);
    return () => clearInterval(interval);
  }, [logBrowserOpen, logBrowserMode, logBrowserServerId]);

  // Modal auto-close on tab change
  useEffect(() => {
    setSelectedItem(null);
  }, [activeTab]);

  const handleControl = async (id: string, action: string) => {
    try {
      setPendingServerAction(prev => ({ ...prev, [id]: action }));
      addNotification(`Sending ${action} command to ${id}...`, 'info');
      const res = await fetch(API_BASE + '/server/control', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, action })
      });
      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        const extra =
          action === 'start'
            ? (data?.note ? ` (${data.note})` : (data?.log_path ? ` (logs: ${data.log_path})` : ''))
            : '';
        addNotification(`Server ${id} ${action === 'start' ? 'started' : 'stopped'}.${extra}`, 'success');
      } else {
        const data = await res.json();
        addNotification(data.error || `Failed to ${action} server.`, 'error');
      }
      fetchData();
    } catch (e) {
      addNotification(String(e), 'error');
    } finally {
      setPendingServerAction(prev => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    }
  };

  const handleAcknowledge = async () => {
    try {
      const res = await fetch(API_BASE + '/nexus/acknowledge', { method: 'POST' });
      if (res.ok) {
        addNotification("Errors acknowledged and cleared from Dashboard.", "success");
        fetchData();
      }
    } catch (e) { addNotification(String(e), "error"); }
  };

  const [opOutputs, setOpOutputs] = useState<Record<string, any>>({});
  const filteredLogs = useMemo(() => {
    return logs.filter(l => {
      const msg = l.message || '';
      const sug = l.suggestion || '';
      const matchText = (msg + sug).toLowerCase().includes(terminalFilter.toLowerCase());
      const matchLevel = terminalLevel === 'ALL' || l.level === terminalLevel;
      return matchText && matchLevel;
    }).slice(-100).reverse();
  }, [logs, terminalFilter, terminalLevel]);

  const fleetHealth = useMemo(() => {
    const servers = (systemStatus?.servers || []) as any[];
    const coreIds = new Set(['mcp-injector', 'mcp-server-manager', 'repo-mcp-packager', 'nexus-librarian']);
    const managed = servers.filter(s => s && !coreIds.has(String(s.id)));
    const total = managed.length;
    const online = managed.filter(s => s.status === 'online').length;
    const stopped = managed.filter(s => s.status !== 'online').length;
    const label = total === 0 ? 'No servers' : (stopped === 0 ? 'All online' : 'Mixed');
    const detail = total === 0 ? '—' : `${online}/${total} online`;
    const pulse = total === 0 ? 'yellow' : (stopped === 0 ? 'green' : 'yellow');
    return { total, online, stopped, label, detail, pulse };
  }, [systemStatus]);

  const handleRun = async (cmd: string, key: string) => {
    try {
      addNotification(`Executing: ${cmd.split(' ')[0]}...`, 'info');
      setOpOutputs(prev => ({ ...prev, [key]: { status: 'running', output: '...' } }));

      const res = await fetch(API_BASE + '/nexus/run', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
      });
      const data = await res.json();

      setOpOutputs(prev => ({
        ...prev,
        [key]: {
          status: data.success ? 'success' : 'error',
          output: data.success ? (data.stdout || 'Success') : (data.stderr || data.error)
        }
      }));

      if (data.success) {
        addNotification("Operation completed successfully.", "success");
      } else {
        addNotification(`Operation failed: ${data.stderr || data.error}`, "error");
      }
      fetchData();
    } catch (e) {
      addNotification(String(e), "error");
      setOpOutputs(prev => ({ ...prev, [key]: { status: 'error', output: String(e) } }));
    }
  };


  const [helpContent, setHelpContent] = useState<string | null>(null);
  const [helpTitle, setHelpTitle] = useState<string | null>(null);

  const fetchHelp = async (bin: string, title: string) => {
    setHelpTitle(title);
    setHelpContent("Loading help...");
    try {
      const res = await fetch(API_BASE + '/nexus/help', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bin })
      });
      const d = await res.json();
      setHelpContent(d.help || d.error || "No help available.");
    } catch (e) { setHelpContent(String(e)); }
  };

  const coreBinForKey = (k: string): { bin: string; title: string; startCmd?: string } | null => {
    const key = String(k || '').toLowerCase();
    if (key === 'activator') return { bin: 'mcp-activator', title: 'Activator' };
    if (key === 'observer') return { bin: 'mcp-observer', title: 'Observer' };
    if (key === 'surgeon') return { bin: 'mcp-surgeon', title: 'Surgeon' };
    if (key === 'librarian_bin') return { bin: 'mcp-librarian', title: 'Librarian (Binary)' };
    if (key === 'librarian') return { bin: 'mcp-librarian', title: 'Librarian (Service)', startCmd: 'mcp-librarian --server' };
    return null;
  };

  return (
    <div className="app-container">
      <div className="liquid-bg"></div>

      {/* Notifications Portal */}
      <div style={{ position: 'fixed', bottom: '24px', right: '24px', zIndex: 1000, display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {notifications.map(n => (
          <div key={n.id} className="glass-card" style={{
            minWidth: '300px', display: 'flex', alignItems: 'center', gap: '12px',
            borderLeft: `4px solid ${n.type === 'success' ? '#10b981' : n.type === 'error' ? '#ef4444' : '#3b82f6'}`,
            padding: '12px 16px', animation: 'slideIn 0.3s ease-out'
          }}>
            {n.type === 'success' ? <CheckCircle2 size={20} color="#10b981" /> : n.type === 'error' ? <AlertTriangle size={20} color="#ef4444" /> : <Info size={20} color="#3b82f6" />}
            <span style={{ fontSize: '14px' }}>{n.message}</span>
            <X size={14} style={{ marginLeft: 'auto', cursor: 'pointer', opacity: 0.5 }} onClick={() => setNotifications(prev => prev.filter(x => x.id !== n.id))} />
          </div>
        ))}
      </div>

      {/* GAP-R2 FIX: Drift Detection Banner — shows when workspace diverges from managed mirror */}
      {driftReport?.any_drift && (
        <div id="drift-banner" style={{
          position: 'fixed', top: 0, left: 0, right: 0, zIndex: 900,
          background: 'linear-gradient(90deg, rgba(245,158,11,0.92), rgba(217,119,6,0.92))',
          backdropFilter: 'blur(8px)', padding: '10px 24px',
          display: 'flex', alignItems: 'center', gap: '12px', fontSize: '13px', color: '#fff',
          boxShadow: '0 2px 12px rgba(0,0,0,0.3)',
        }}>
          <AlertTriangle size={16} style={{ flexShrink: 0 }} />
          <span style={{ fontWeight: 600 }}>⚠️ Drift Detected</span>
          <span style={{ opacity: 0.9 }}>
            {driftReport.repos.filter((r: any) => r.drifted).map((r: any) => r.repo).join(', ')} — workspace source differs from managed mirror (~/.mcp-tools).
          </span>
          <code style={{ background: 'rgba(0,0,0,0.25)', borderRadius: '4px', padding: '2px 8px', fontFamily: 'monospace', fontSize: '12px' }}>
            {driftReport.repair_command}
          </code>
          <span style={{ marginLeft: 'auto', opacity: 0.7, fontSize: '11px' }}>Run repair to sync · Last checked: {new Date().toLocaleTimeString()}</span>
        </div>
      )}

      {/* Stacked side-panels (no screen dimming). */}
      {(helpContent || logViewer || selectedItem || purgeModalOpen || sideConfirm || logBrowserOpen || selectedLogEntry) && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            right: 0,
            height: '100vh',
            display: 'flex',
            flexDirection: 'row-reverse',
            gap: '12px',
            zIndex: 6000,
            pointerEvents: 'none',
          }}
        >
          {logBrowserOpen && (
            <div
              className="glass-card"
              style={{
                width: '520px',
                height: 'calc(100vh - 24px)',
                marginTop: '12px',
                marginBottom: '12px',
                borderLeft: '1px solid rgba(59,130,246,0.45)',
                background: 'rgba(10, 10, 20, 0.95)',
                display: 'flex',
                flexDirection: 'column',
                animation: 'slideInRight 0.3s ease-out',
                borderRadius: '14px 0 0 14px',
                pointerEvents: 'auto',
              }}
            >
              <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
                    <Terminal size={16} /> Log Browser
                  </h3>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '6px' }}>
                    View raw logs and reports without leaving Nexus Commander.
                  </div>
                </div>
                <button className="nav-item" style={{ padding: '6px 10px', fontSize: '11px' }} onClick={() => setLogBrowserOpen(false)}>Close</button>
              </div>

              <div style={{ padding: '12px 20px', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', gap: '10px', alignItems: 'center' }}>
                <select className="glass-card" style={{ padding: '8px 10px', fontSize: '12px', background: 'rgba(0,0,0,0.25)' }} value={logBrowserMode} onChange={e => openLogBrowser(e.target.value as any, logBrowserServerId)}>
                  <option value="audit">Audit report (JSON)</option>
                  <option value="lifecycle">Server lifecycle log</option>
                </select>
                <select className="glass-card" style={{ flex: 1, padding: '8px 10px', fontSize: '12px', background: 'rgba(0,0,0,0.25)' }} value={logBrowserServerId} onChange={e => openLogBrowser(logBrowserMode, e.target.value)}>
                  <option value="">(system-wide)</option>
                  {(systemStatus?.servers || []).map((s: any) => (
                    <option key={s.id} value={s.id}>{s.name} ({s.id})</option>
                  ))}
                </select>
                <button className="nav-item" style={{ padding: '8px 12px', fontSize: '12px' }} onClick={() => openLogBrowser(logBrowserMode, logBrowserServerId)}>
                  Refresh
                </button>
              </div>

              <pre style={{ flex: 1, margin: 0, padding: '16px 20px', overflow: 'auto', fontFamily: 'ui-monospace, Menlo, monospace', fontSize: '11px', background: 'rgba(0,0,0,0.45)', color: '#e5e7eb', whiteSpace: 'pre-wrap' }}>
                {logBrowserPayload || '(no data)'}
              </pre>
            </div>
          )}


          {selectedLogEntry && (
            <div
              className="glass-card"
              style={{
                width: '460px',
                height: 'calc(100vh - 24px)',
                marginTop: '12px',
                marginBottom: '12px',
                borderLeft: '1px solid rgba(59,130,246,0.45)',
                background: 'rgba(10, 10, 20, 0.95)',
                display: 'flex',
                flexDirection: 'column',
                animation: 'slideInRight 0.3s ease-out',
                borderRadius: '14px 0 0 14px',
                pointerEvents: 'auto',
              }}
            >
              <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
                    <Terminal size={16} /> Log Entry
                  </h3>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '6px' }}>
                    {new Date((selectedLogEntry.timestamp || 0) * 1000).toLocaleString()} • {selectedLogEntry.level}
                  </div>
                </div>
                <button className="nav-item" style={{ padding: '6px 10px', fontSize: '11px' }} onClick={() => setSelectedLogEntry(null)}>Close</button>
              </div>
              <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                <div style={{ fontSize: '13px', fontWeight: 600 }}>{selectedLogEntry.message}</div>
              </div>
              <pre style={{ flex: 1, margin: 0, padding: '16px 20px', overflow: 'auto', fontFamily: 'ui-monospace, Menlo, monospace', fontSize: '11px', background: 'rgba(0,0,0,0.45)', color: '#e5e7eb', whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(selectedLogEntry, null, 2)}
              </pre>
            </div>
          )}

          {sideConfirm && (
            <div
              className="glass-card"
              style={{
                width: '520px',
                height: 'calc(100vh - 24px)',
                marginTop: '12px',
                marginBottom: '12px',
                borderLeft: `1px solid ${sideConfirm.danger ? 'rgba(239,68,68,0.55)' : 'rgba(59,130,246,0.45)'}`,
                background: 'rgba(10, 10, 20, 0.95)',
                display: 'flex',
                flexDirection: 'column',
                animation: 'slideInRight 0.3s ease-out',
                borderRadius: '14px 0 0 14px',
                pointerEvents: 'auto',
              }}
            >
              <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
                <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
                  {sideConfirm.danger ? <AlertTriangle size={16} color="#ef4444" /> : <Info size={16} />} {sideConfirm.title}
                </h3>
                <button className="nav-item" style={{ padding: '6px 10px', fontSize: '11px' }} onClick={() => setSideConfirm(null)}>Close</button>
              </div>
              {sideConfirm.details && (
                <pre style={{ margin: 0, padding: '16px 20px', overflow: 'auto', fontFamily: 'ui-monospace, Menlo, monospace', fontSize: '11px', background: 'rgba(0,0,0,0.35)', color: '#e5e7eb', whiteSpace: 'pre-wrap', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                  {sideConfirm.details}
                </pre>
              )}
              <div style={{ padding: '16px 20px', display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button className="nav-item" onClick={() => setSideConfirm(null)}>{sideConfirm.cancelLabel || 'Cancel'}</button>
                <button
                  className="nav-item"
                  style={sideConfirm.danger ? { borderColor: 'rgba(239,68,68,0.65)', color: '#ef4444' } : { borderColor: 'rgba(59,130,246,0.65)', color: '#3b82f6' }}
                  onClick={async () => {
                    const fn = sideConfirm.onConfirm;
                    setSideConfirm(null);
                    if (fn) await fn();
                  }}
                >
                  {sideConfirm.confirmLabel || 'Confirm'}
                </button>
              </div>
            </div>
          )}

          {purgeModalOpen && (
            <div
              className="glass-card"
              style={{
                width: 'min(760px, 96vw)',
                height: 'calc(100vh - 24px)',
                marginTop: '12px',
                marginBottom: '12px',
                borderLeft: '1px solid rgba(239, 68, 68, 0.45)',
                background: 'rgba(10, 10, 18, 0.95)',
                display: 'flex',
                flexDirection: 'column',
                animation: 'slideInRight 0.3s ease-out',
                borderRadius: '14px 0 0 14px',
                pointerEvents: 'auto',
                overflow: 'auto',
              }}
            >
              <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
                <div>
                  <h3 style={{ margin: 0, color: '#ef4444' }}>Factory Reset</h3>
                  <p style={{ margin: '8px 0 0', fontSize: '12px', color: 'var(--text-dim)' }}>Guided uninstall. Choose what to remove, then confirm.</p>
                </div>
                <button className="nav-item" onClick={() => setPurgeModalOpen(false)} style={{ padding: '6px 10px' }}>Close</button>
              </div>
              <div style={{ padding: '16px 20px', display: 'grid', gridTemplateColumns: '1fr', gap: '10px' }}>
                <div className="glass-card" style={{ padding: '12px', background: 'rgba(255,255,255,0.02)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
                    <div style={{ minWidth: 0 }}>
                      <b style={{ fontSize: '12px' }}>Preset</b>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                        Defaults to env reset (keeps suite). Full wipe is for a clean reinstall.
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                      <button
                        className="nav-item"
                        onClick={() =>
                          setPurgeOptions((o: any) => ({
                            ...o,
                            purge_data: false,
                            purge_env: true,
                            detach_clients: false,
                            detach_managed_servers: true,
                            detach_suite_tools: false,
                            remove_path_block: false,
                            remove_wrappers: false,
                          }))
                        }
                      >
                        Env reset (default)
                      </button>
                      <button
                        className="nav-item"
                        style={{ borderColor: 'rgba(239,68,68,0.6)', color: '#ef4444' }}
                        onClick={() =>
                          setPurgeOptions({
                            purge_data: true,
                            purge_env: true,
                            kill_venv: true,
                            detach_clients: true,
                            detach_managed_servers: true,
                            detach_suite_tools: true,
                            remove_path_block: true,
                            remove_wrappers: true,
                          } as any)
                        }
                      >
                        Full wipe
                      </button>
                    </div>
                  </div>
                </div>

                <div className="glass-card" style={{ padding: '14px', background: 'rgba(255,255,255,0.02)' }}>
                  <b style={{ fontSize: '12px' }}>What to remove</b>
                  <div style={{ marginTop: '10px', display: 'grid', gap: '10px' }}>
                    <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                      <input
                        type="checkbox"
                        checked={purgeOptions.purge_env}
                        onChange={(e) => setPurgeOptions((o: any) => ({ ...o, purge_env: e.target.checked }))}
                        style={{ marginTop: '2px' }}
                      />
                      <div>
                        <div style={{ fontSize: '12px' }}>
                          <b>Reset environments (keep suite installed)</b> <span style={{ opacity: 0.7 }}>(recommended)</span>
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '3px' }}>
                          Deletes per-server venvs and runtime state but keeps Nexus Commander + suite tools installed.
                        </div>
                      </div>
                    </label>

                    <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                      <input
                        type="checkbox"
                        checked={purgeOptions.purge_data}
                        onChange={(e) => setPurgeOptions((o: any) => ({ ...o, purge_data: e.target.checked }))}
                        style={{ marginTop: '2px' }}
                      />
                      <div>
                        <div style={{ fontSize: '12px' }}>
                          <b>Wipe central Nexus data</b> <span style={{ opacity: 0.7 }}>(full uninstall / clean reinstall)</span>
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '3px' }}>
                          Removes state under <code>~/.mcp-tools</code> including manifests, inventory and logs.
                        </div>
                      </div>
                    </label>

                    <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                      <input
                        type="checkbox"
                        checked={purgeOptions.detach_managed_servers}
                        onChange={(e) => setPurgeOptions((o: any) => ({ ...o, detach_managed_servers: e.target.checked }))}
                        style={{ marginTop: '2px' }}
                      />
                      <div>
                        <div style={{ fontSize: '12px' }}>
                          <b>Detach managed servers</b> <span style={{ opacity: 0.7 }}>(safe)</span>
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '3px' }}>
                          Removes server entries that were created/managed under <code>~/.mcp-tools/servers</code>.
                        </div>
                      </div>
                    </label>

                    <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                      <input
                        type="checkbox"
                        checked={purgeOptions.detach_suite_tools}
                        onChange={(e) => setPurgeOptions((o: any) => ({ ...o, detach_suite_tools: e.target.checked }))}
                        style={{ marginTop: '2px' }}
                      />
                      <div>
                        <div style={{ fontSize: '12px' }}>
                          <b>Detach suite tools from IDE clients</b> <span style={{ opacity: 0.7 }}>(optional)</span>
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '3px' }}>
                          Removes <code>nexus-*</code> tool entries and commands pointing into <code>~/.mcp-tools/bin</code>. Use this only if you want IDEs fully clean.
                        </div>
                      </div>
                    </label>

                    <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                      <input
                        type="checkbox"
                        checked={purgeOptions.detach_clients}
                        onChange={(e) => setPurgeOptions((o: any) => ({ ...o, detach_clients: e.target.checked }))}
                        style={{ marginTop: '2px' }}
                      />
                      <div>
                        <div style={{ fontSize: '12px' }}>
                          <b>Detach everything Nexus-related from IDE clients</b> <span style={{ opacity: 0.7 }}>(broad)</span>
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '3px' }}>
                          Broad heuristic: removes entries pointing anywhere inside <code>~/.mcp-tools</code>. This is mainly for full wipe recovery.
                        </div>
                      </div>
                    </label>

                    <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                      <input
                        type="checkbox"
                        checked={purgeOptions.remove_path_block}
                        onChange={(e) => setPurgeOptions((o: any) => ({ ...o, remove_path_block: e.target.checked }))}
                        style={{ marginTop: '2px' }}
                      />
                      <div>
                        <div style={{ fontSize: '12px' }}>
                          <b>Remove PATH block</b>
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '3px' }}>
                          Removes the Nexus-managed shell snippet from <code>~/.zshrc</code> / <code>~/.bashrc</code> that adds <code>~/.mcp-tools/bin</code> to your PATH.
                        </div>
                      </div>
                    </label>

                    <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                      <input
                        type="checkbox"
                        checked={purgeOptions.remove_wrappers}
                        onChange={(e) => setPurgeOptions((o: any) => ({ ...o, remove_wrappers: e.target.checked }))}
                        style={{ marginTop: '2px' }}
                      />
                      <div>
                        <div style={{ fontSize: '12px' }}>
                          <b>Remove PATH wrappers</b>
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '3px' }}>
                          Wrapper scripts are tiny launchers in <code>~/.local/bin</code> (e.g., <code>mcp-surgeon</code>) that forward to the real suite binaries. They let commands work “from anywhere”.
                        </div>
                      </div>
                    </label>
                  </div>
                </div>

                <div className="glass-card" style={{ padding: '14px', background: 'rgba(255,255,255,0.02)' }}>
                  <b style={{ fontSize: '12px' }}>Confirm</b>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '6px' }}>
                    Type <code>PURGE</code> to enable the reset button.
                  </div>
                  <input
                    value={purgeConfirmText}
                    onChange={(e) => setPurgeConfirmText(e.target.value)}
                    placeholder="Type PURGE"
                    style={{
                      marginTop: '10px',
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '10px',
                      border: '1px solid rgba(255,255,255,0.12)',
                      background: 'rgba(0,0,0,0.25)',
                      color: 'var(--text)',
                      outline: 'none',
                    }}
                  />
                </div>

                <div className="glass-card" style={{ padding: '14px', background: 'rgba(255,255,255,0.02)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
                    <div>
                      <b style={{ fontSize: '12px' }}>Preview plan (recommended)</b>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                        Runs a dry-run: shows exactly what would be removed, without deleting anything.
                      </div>
                    </div>
                    <button
                      className="nav-item"
                      disabled={purgePreviewLoading}
                      onClick={async () => {
                        try {
                          setPurgePreview(null);
                          setPurgePreviewLoading(true);
                          const res = await fetch(API_BASE + '/system/uninstall', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ ...purgeOptions, dry_run: true }),
                          });
                          const d = await res.json().catch(() => ({}));
                          const ok = !!d?.success;
                          const raw = (() => {
                            try { return JSON.stringify(d, null, 2); } catch { return String(d); }
                          })();
                          setPurgePreview({ ok, stdout: String(d?.stdout || ''), stderr: String(d?.stderr || d?.error || ''), raw });
                          addNotification(ok ? "Preview generated." : "Preview failed.", ok ? "success" : "error");
                        } catch (e) {
                          setPurgePreview({ ok: false, stdout: "", stderr: String(e), raw: String(e) });
                          addNotification(String(e), "error");
                        } finally {
                          setPurgePreviewLoading(false);
                        }
                      }}
                      style={{ padding: '8px 12px' }}
                    >
                      {purgePreviewLoading ? "Generating…" : "Preview"}
                    </button>
                  </div>

                  {purgePreview && (
                    <div style={{ marginTop: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span className={`badge ${purgePreview?.ok ? 'badge-success' : 'badge-danger'}`}>
                          {purgePreview?.ok ? 'dry-run ok' : 'dry-run failed'}
                        </span>
                        <button
                          className="nav-item"
                          onClick={() => {
                            const text = [purgePreview?.raw || "", purgePreview?.stdout || "", purgePreview?.stderr || ""].filter(Boolean).join("\n");
                            navigator.clipboard?.writeText(text);
                            addNotification("Copied preview output.", "success");
                          }}
                          style={{ padding: '6px 10px' }}
                        >
                          Copy
                        </button>
                      </div>
                      <pre style={{ marginTop: '10px', maxHeight: '220px', overflow: 'auto', padding: '12px', borderRadius: '10px', background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.08)', fontSize: '11px', whiteSpace: 'pre-wrap' }}>
                        {(purgePreview?.stdout || "").trim() || "(no stdout)"}
                        {purgePreview?.stderr ? `\n\n[stderr]\n${purgePreview?.stderr?.trim()}` : ""}
                      </pre>
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '4px' }}>
                  <button className="nav-item" onClick={() => setPurgeModalOpen(false)}>
                    Cancel
                  </button>
                  <button
                    className="nav-item"
                    disabled={purgeConfirmText.trim().toUpperCase() !== "PURGE"}
                    style={{
                      borderColor: '#ef4444',
                      color: '#ef4444',
                      opacity: purgeConfirmText.trim().toUpperCase() !== "PURGE" ? 0.55 : 1,
                      cursor: purgeConfirmText.trim().toUpperCase() !== "PURGE" ? 'not-allowed' : 'pointer',
                    }}
                    onClick={async () => {
                      try {
                        addNotification("Factory reset started...", "error");
                        const res = await fetch(API_BASE + '/system/uninstall', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify(purgeOptions),
                        });
                        const d = await res.json().catch(() => ({}));
                        if (!res.ok || !d?.success) {
                          addNotification(d?.error || d?.stderr || "Factory reset failed", "error");
                          return;
                        }
                        addNotification("Factory reset complete. Reloading...", "success");
                        setPurgeModalOpen(false);
                        setTimeout(() => window.location.reload(), 750);
                      } catch (e) {
                        addNotification(String(e), "error");
                      }
                    }}
                  >
                    Confirm reset
                  </button>
                </div>
              </div>
            </div>
          )}

          {selectedItem && (
            <div
              className="glass-card"
              style={{
                width: '720px',
                height: '100vh',
                borderLeft: '1px solid rgba(16,185,129,0.45)',
                background: 'rgba(10, 10, 18, 0.95)',
                display: 'flex',
                flexDirection: 'column',
                animation: 'slideInRight 0.3s ease-out',
                borderRadius: '0',
                pointerEvents: 'auto',
              }}
            >
              <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
                  <ShieldCheck size={16} color="#10b981" /> System Inspector
                </h3>
                <button className="nav-item" onClick={() => setSelectedItem(null)} style={{ padding: '6px 10px' }} aria-label="Close">
                  <X size={16} />
                </button>
              </div>
              <pre style={{ padding: '16px 20px', overflow: 'auto', flex: 1, fontFamily: 'ui-monospace, Menlo, monospace', fontSize: '11px', color: '#e2e8f0', whiteSpace: 'pre-wrap', margin: 0 }}>
                {JSON.stringify(selectedItem, null, 2)}
              </pre>
            </div>
          )}

          {logViewer && (
            <div
              className="glass-card"
              style={{
                width: '720px',
                height: '100vh',
                borderLeft: '1px solid var(--primary)',
                background: 'rgba(10, 10, 20, 0.95)',
                display: 'flex',
                flexDirection: 'column',
                animation: 'slideInRight 0.3s ease-out',
                borderRadius: '0',
                pointerEvents: 'auto',
              }}
            >
              <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
                  <Terminal size={16} /> Last Start Log: {logViewer.serverId}
                </h3>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <button className="nav-item" style={{ padding: '6px 10px', fontSize: '11px' }} onClick={() => openLastStartLog(logViewer.serverId)} title="Refresh">Refresh</button>
                  <button className="nav-item" onClick={() => setLogViewer(null)} style={{ padding: '6px 10px' }} aria-label="Close">
                    <X size={16} />
                  </button>
                </div>
              </div>
              <div style={{ padding: '10px 20px', fontSize: '11px', opacity: 0.7, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                  <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Path: <code>{logViewer.data?.log_path || '(unknown)'}</code></span>
                  <span>MTime: {logViewer.data?.mtime ? new Date(logViewer.data.mtime * 1000).toLocaleString() : '(unknown)'}</span>
                </div>
              </div>
              <pre style={{
                padding: '16px 20px', overflow: 'auto', flex: 1,
                fontFamily: 'ui-monospace, Menlo, monospace', fontSize: '11px',
                color: '#e2e8f0', whiteSpace: 'pre-wrap', margin: 0
              }}>
                {(logViewer.data?.lines || []).join('\n')}
              </pre>
            </div>
          )}

          {helpContent && (
            <div
              className="glass-card"
              style={{
                width: '500px',
                height: '100vh',
                borderLeft: '1px solid var(--primary)',
                background: 'rgba(10, 10, 20, 0.95)',
                display: 'flex',
                flexDirection: 'column',
                animation: 'slideInRight 0.3s ease-out',
                borderRadius: '0',
                pointerEvents: 'auto',
              }}
            >
              <div style={{ padding: '20px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Info size={18} /> {helpTitle} Help
                </h3>
                <button className="nav-item" onClick={() => setHelpContent(null)} style={{ padding: '6px 10px' }} aria-label="Close">
                  <X size={16} />
                </button>
              </div>
              <pre style={{
                padding: '20px', overflow: 'auto', flex: 1,
                fontFamily: 'ui-monospace, Menlo, monospace', fontSize: '11px',
                color: '#e2e8f0', whiteSpace: 'pre-wrap'
              }}>
                {helpContent}
              </pre>
            </div>
          )}
        </div>
      )}

      <aside className="sidebar">
        <div className="brand" style={{ cursor: 'pointer' }} onClick={() => setActiveTab('dashboard')}><ShieldCheck size={32} /> <span>Nexus Commander</span></div>
        <nav className="nav-group">
          <div className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')} style={{ position: 'relative' }}><LayoutDashboard size={20} /> Dashboard{healthIssues.some(h => h.status === 'fatal' || h.status === 'error') && (<span className="pulse-dot pulse-red dash-health-dot" style={{ position: 'absolute', top: 12, right: 12, width: 6, height: 6 }}></span>)}</div>
          <div className={`nav-item ${activeTab === 'librarian' ? 'active' : ''}`} onClick={() => setActiveTab('librarian')}><Library size={20} /> Librarian</div>
          <div className={`nav-item ${activeTab === 'operations' ? 'active' : ''}`} onClick={() => setActiveTab('operations')} style={{ position: 'relative' }}>
            <Activity size={20} /> Operations

          </div>
          <div className={`nav-item ${activeTab === 'terminal' ? 'active' : ''}`} onClick={() => setActiveTab('terminal')}><Terminal size={20} /> Command Log</div>
          <div className={`nav-item ${activeTab === 'forge' ? 'active' : ''}`} onClick={() => setActiveTab('forge')}><Cpu size={20} /> Forge Engine</div>
          <div className={`nav-item ${activeTab === 'lifecycle' ? 'active' : ''}`} onClick={() => setActiveTab('lifecycle')} style={{ position: 'relative' }}>
            <Settings size={20} /> Lifecycle
            {systemStatus?.updateAvailable && (
              <span className="pulse-dot pulse-blue" style={{ position: 'absolute', top: 12, right: 12, width: 6, height: 6 }}></span>
            )}
          </div>
        </nav>

        <div style={{ marginTop: 'auto', padding: '0 16px', fontSize: '10px', color: 'var(--text-dim)', opacity: 0.5, letterSpacing: '0.5px' }}>
          CORE v{systemStatus?.version || '0.0.0'}
        </div>
      </aside>



      {/* Content area: main + metric side panel side-by-side */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' }}>
        <main className="main-viewport" style={{ flex: 1, overflow: 'hidden auto' }}>
          <header style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '32px', alignItems: 'center' }}>
            <div>
              <h1 style={{ fontSize: '28px', background: 'linear-gradient(90deg, #fff, var(--text-dim))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Nexus Commander</h1>
              <p style={{ color: 'var(--text-dim)', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                {systemStatus?.posture || 'Disconnected'}
                <span className={`pulse-dot pulse-${systemStatus?.pulse || 'red'}`}></span>
              </p>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
                <div style={{ fontSize: '10px', letterSpacing: '0.5px', textTransform: 'uppercase', opacity: 0.6 }}>Active project</div>
                <select className="glass-card" style={{ padding: '8px 16px', background: 'rgba(255,255,255,0.05)', cursor: 'pointer' }} value={systemStatus?.active_project?.id} onChange={e => {
                  const p = projects.find(x => x.id === e.target.value);
                  if (p) {
                    fetch(API_BASE + '/nexus/projects', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: p.id, path: p.path }) }).then(() => {
                      addNotification(`Switched to project: ${p.id}`, 'info');
                      fetchData();
                    });
                  }
                }}>
                  {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
            </div>
          </header>

          {activeTab === 'dashboard' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {healthIssues.filter(h => h.status === 'fatal').length > 0 && (
                <section className="glass-card" style={{ border: '1px solid var(--warning)', background: 'rgba(239,68,68,0.1)', animation: 'pulse 3s infinite' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h3 style={{ color: '#ef4444', display: 'flex', gap: '10px', margin: 0 }}><AlertTriangle size={20} /> SYSTEM RECOVERY REQUIRED</h3>
                    <button className="nav-item" style={{ fontSize: '11px', padding: '4px 12px', opacity: 0.8, position: 'relative', zIndex: 10 }} onClick={handleAcknowledge}>Acknowledge Fatal Errors</button>
                  </div>
                  {healthIssues.filter(h => h.status === 'fatal').map((issue, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <span><b style={{ color: '#ef4444' }}>[{issue.domain}]</b> {issue.msg}</span>
                      <button className="nav-item badge-warning" style={{ fontSize: '11px', padding: '4px 12px' }}>ACTION: {issue.fix}</button>
                    </div>
                  ))}
                </section>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '24px' }}>
                <div className="glass-card metrics-card" onClick={() => openMetricPanel('cpu')} style={{ cursor: 'pointer' }}>
                  <Cpu size={24} color="var(--primary)" />
                  <span style={{ fontSize: '26px', fontWeight: 700, margin: '12px 0 4px', display: 'block' }}>{systemStatus?.metrics?.cpu ?? 0}%</span>
                  <p style={{ color: 'var(--text-dim)', fontSize: '12px', display: 'flex', justifyContent: 'space-between', width: '100%', margin: '0' }}>
                    CPU Usage <Sparkline data={(systemStatus?.history || []).map((h: any) => h.cpu)} color="var(--primary)" width={60} height={20} />
                  </p>
                </div>
                <div className="glass-card metrics-card" onClick={() => openMetricPanel('ram')} style={{ cursor: 'pointer' }}>
                  <Monitor size={24} color="var(--success)" />
                  <span style={{ fontSize: '26px', fontWeight: 700, margin: '12px 0 4px', display: 'block' }}>
                    {((systemStatus?.metrics?.ram_used ?? 0) / 1024 / 1024 / 1024).toFixed(1)} GB
                  </span>
                  <p style={{ color: 'var(--text-dim)', fontSize: '12px', margin: 0 }}>
                    / {((systemStatus?.metrics?.ram_total ?? 0) / 1024 / 1024 / 1024).toFixed(1)} GB RAM
                  </p>
                </div>
                <div className="glass-card metrics-card" onClick={() => openMetricPanel('disk')} style={{ cursor: 'pointer' }}>
                  <HardDrive size={24} color="#a855f7" />
                  <span style={{ fontSize: '26px', fontWeight: 700, margin: '12px 0 4px', display: 'block' }}>
                    {((systemStatus?.metrics?.disk_used ?? 0) / 1024 / 1024 / 1024).toFixed(0)} GB
                  </span>
                  <p style={{ color: 'var(--text-dim)', fontSize: '12px', margin: 0 }}>
                    / {((systemStatus?.metrics?.disk_total ?? 0) / 1024 / 1024 / 1024).toFixed(0)} GB Used
                  </p>
                </div>
                <div className="glass-card metrics-card" style={{ position: 'relative', cursor: 'pointer' }} onClick={() => openMetricPanel('health')}>
                  <Globe size={24} color="#3b82f6" />
                  <span style={{ fontSize: '26px', fontWeight: 700, margin: '12px 0 4px', display: 'block' }}>{fleetHealth.label}</span>
                  <p style={{ color: 'var(--text-dim)', fontSize: '12px', margin: 0 }}>Fleet Health · {fleetHealth.detail}</p>
                </div>
              </div>

              <section className="glass-card" style={{ padding: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <h3 style={{ margin: 0, display: 'flex', gap: '10px', alignItems: 'center' }}><ShieldCheck size={18} /> Core Components</h3>
                  <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Always visible</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                  {Object.entries(systemStatus?.core_components || {}).map(([k, v]) => (
                    <div
                      key={k}
                      className="glass-card"
                      style={{ padding: '12px', background: 'rgba(255,255,255,0.03)', cursor: 'pointer', border: coreDrawerKey === k ? '1px solid rgba(59,130,246,0.45)' : undefined }}
                      onClick={() => setCoreDrawerKey(prev => (prev === k ? null : k))}
                      title="Click for health actions"
                    >
                      <div style={{ fontSize: '11px', letterSpacing: '0.5px', textTransform: 'uppercase', color: 'var(--text-dim)' }}>{k.replace(/_/g, ' ')}</div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
                        <span style={{ fontWeight: 600 }}>{String(v)}</span>
                        <span className={`pulse-dot pulse-${v === 'online' ? 'green' : v === 'stopped' ? 'yellow' : 'red'}`} style={{ width: 6, height: 6 }}></span>
                      </div>
                    </div>
                  ))}
                </div>

                {coreDrawerKey && (
                  <div className="glass-card" style={{ marginTop: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(59,130,246,0.45)', animation: 'slideIn 0.2s ease-out' }}>
                    <div style={{ padding: '12px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                          {coreDrawerKey.replace(/_/g, ' ')}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                          Human workflow: verify status → view last-known evidence → attempt recovery.
                        </div>
                      </div>
                      <button className="nav-item" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => setCoreDrawerKey(null)}>Close</button>
                    </div>
                    <div style={{ padding: '0 14px 12px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                      <button className="nav-item" style={{ padding: '6px 10px', fontSize: '11px' }} onClick={() => { setActiveTab('terminal'); setTerminalFilter(coreDrawerKey); }}>
                        View timeline (filtered)
                      </button>
                      <button className="nav-item" style={{ padding: '6px 10px', fontSize: '11px' }} onClick={() => openLogBrowser('audit')}>
                        Open raw audit (JSON)
                      </button>
                      {(() => {
                        const meta = coreBinForKey(coreDrawerKey);
                        if (!meta) return null;
                        return (
                          <>
                            <button className="nav-item" style={{ padding: '6px 10px', fontSize: '11px' }} onClick={() => fetchHelp(meta.bin, meta.title)}>
                              Show help
                            </button>
                            {meta.startCmd && String((systemStatus?.core_components || {})[coreDrawerKey]) !== 'online' && (
                              <button className="nav-item badge-success" style={{ padding: '6px 10px', fontSize: '11px' }} onClick={() => handleRun(meta.startCmd || '', `core-${coreDrawerKey}-start`)}>
                                Attempt start
                              </button>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </div>
                )}
              </section>

              <section className="glass-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <h3 style={{ margin: 0 }}>Active Inventory</h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span className="badge-dim badge" style={{ fontSize: '10px' }}>{(systemStatus?.servers || []).length} Registered</span>
                    <div style={{ display: 'flex', gap: '4px', background: 'rgba(255,255,255,0.05)', padding: '3px', borderRadius: '8px' }}>
                      <button onClick={() => setInventoryView('card')} title="Card View" style={{ padding: '4px 8px', borderRadius: '6px', border: 'none', cursor: 'pointer', background: inventoryView === 'card' ? 'rgba(59,130,246,0.2)' : 'transparent', color: inventoryView === 'card' ? 'var(--primary)' : 'var(--text-dim)', transition: 'all 0.2s' }}>
                        <LayoutDashboard size={14} />
                      </button>
                      <button onClick={() => setInventoryView('list')} title="List View" style={{ padding: '4px 8px', borderRadius: '6px', border: 'none', cursor: 'pointer', background: inventoryView === 'list' ? 'rgba(59,130,246,0.2)' : 'transparent', color: inventoryView === 'list' ? 'var(--primary)' : 'var(--text-dim)', transition: 'all 0.2s' }}>
                        <Activity size={14} />
                      </button>
                    </div>
                  </div>
                </div>
                {/* Card View */}
                {inventoryView === 'card' && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
                    {(systemStatus?.servers || []).map((s: any) => {
                      const isInjecting = injectTarget?.id === s.id;

                      return (
                        <div key={s.id} className="glass-card metrics-card" style={{ padding: '20px', borderLeft: `4px solid ${s.status === 'online' ? '#10b981' : '#ef4444'}` }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div style={{ wordBreak: 'break-all', display: 'flex', alignItems: 'flex-start', gap: '10px', minWidth: 0 }}>
                              <div style={{ minWidth: 0 }}>
                                <b style={{ fontSize: '16px' }}>{s.name}</b>
                                <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '4px' }}>TYPE: {(s.type || 'server').toUpperCase()}</div>
                                <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px', opacity: 0.7 }}>{s.raw?.path || s.id}</div>
                              </div>
                              {!['mcp-injector', 'mcp-server-manager', 'repo-mcp-packager'].includes(s.id) && (
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '2px', flexShrink: 0 }}>
                                  <button
                                    className={`nav-item ${isInjecting ? 'active' : 'badge-command'}`}
                                    style={{ padding: '6px 10px', fontSize: '11px', display: 'flex', gap: '6px', alignItems: 'center' }}
                                    onClick={() => {
                                      if (isInjecting) {
                                        setInjectTarget(null);
                                      } else {
                                        setInjectTarget(s);
                                        setInjectionStatus(null);
                                        fetch(API_BASE + '/injector/clients').then(r => r.json()).then(d => {
                                          setAvailableClients(d.clients || []);
                                          if (d.clients && d.clients.length > 0) setTargetClient(d.clients[0]);
                                        });
                                        fetch(API_BASE + '/injector/status', {
                                          method: 'POST', headers: { 'Content-Type': 'application/json' },
                                          body: JSON.stringify({ server_id: s.id, name: s.name })
                                        }).then(r => r.json()).then(d => setInjectionStatus(d));
                                      }
                                    }}
                                    title="Inject to IDE"
                                  >
                                    <Activity size={12} /> {isInjecting ? 'Close' : 'Inject'}
                                  </button>
                                  <button
                                    className="nav-item"
                                    style={{ padding: '6px 10px', fontSize: '11px', color: 'var(--danger)' }}
                                    onClick={() => {
                                      openConfirmPanel({
                                        title: `Remove "${s.name}" from inventory?`,
                                        danger: true,
                                        confirmLabel: 'Remove',
                                        details: `Server ID: ${s.id}`,
                                        onConfirm: async () => {
                                          const res = await fetch(API_BASE + '/server/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: s.id }) });
                                          if (res.ok) { addNotification(`Removed ${s.name}.`, 'success'); fetchData(); }
                                          else { const d = await res.json(); addNotification(d.error || 'Failed.', 'error'); }
                                        }
                                      });
                                    }}
                                    title="Remove from inventory"
                                  >
                                    <Trash2 size={14} />
                                  </button>
                                </div>
                              )}
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                              <span className={`badge ${s.status === 'online' ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: '10px' }}>{s.status}</span>
                              {s.metrics?.pid && (
                                <div style={{ display: 'flex', gap: '4px' }}>
                                  <span className="badge badge-dim" style={{ fontSize: '9px' }}>PID: {s.metrics.pid}</span>
                                  <span className="badge badge-dim" style={{ fontSize: '9px' }}>CPU: {s.metrics.cpu?.toFixed(1) ?? 0}%</span>
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Controls Row */}
                          <div style={{ marginTop: '20px', display: 'flex', gap: '8px' }}>
                            <button
                              className={`nav-item ${s.status === 'online' ? 'badge-danger' : 'badge-primary'}`}
                              style={{ flex: 1, justifyContent: 'center', fontSize: '12px', opacity: pendingServerAction[s.id] ? 0.6 : 1 }}
                              disabled={!!pendingServerAction[s.id]}
                              onClick={() => handleControl(s.id, s.status === 'online' ? 'stop' : 'start')}
                              title={pendingServerAction[s.id] ? `Working: ${pendingServerAction[s.id]}` : undefined}
                            >
                              {pendingServerAction[s.id]
                                ? (pendingServerAction[s.id] === 'start' ? 'Starting…' : 'Stopping…')
                                : (s.status === 'online' ? 'Stop' : 'Start')}
                            </button>

                            {/* Lifecycle Log */}
                            <button className="nav-item" style={{ padding: '8px' }} onClick={() => openServerDrawer(s.id, 'log')} title="View lifecycle log">
                              <Terminal size={18} />
                            </button>

                            {/* Per-server upgrade (server-scoped, not global) */}
                            {!['mcp-injector', 'mcp-server-manager', 'repo-mcp-packager'].includes(s.id) ? (
                              <button
                                className="nav-item"
                                style={{ padding: '8px' }}
                                onClick={async () => {
                                  addNotification(`Upgrading ${s.name}…`, 'info');
                                  try {
                                    const res = await fetch(API_BASE + `/server/update/${encodeURIComponent(s.id)}`, { method: 'POST' });
                                    const d = await res.json().catch(() => ({}));
                                    addNotification(d.message || d.error || 'Upgrade started.', res.ok && d.success ? 'success' : 'error');
                                  } catch (e) { addNotification(String(e), 'error'); }
                                }}
                                title="Upgrade this server’s Python deps (server-scoped)"
                              >
                                <Wrench size={18} />
                              </button>
                            ) : null}

                            {/* Audit Report */}
                            <button
                              className="nav-item"
                              style={{ padding: '8px' }}
                              onClick={() => openServerDrawer(s.id, 'report')}
                              title="Open audit report"
                            >
                              <FileText size={18} />
                            </button>

                            <button className="nav-item" style={{ padding: '8px' }} onClick={() => openServerDrawer(s.id, 'inspect', s.raw)} title="Inspect">
                              <Search size={18} />
                            </button>

                            {['mcp-injector', 'mcp-server-manager', 'repo-mcp-packager'].includes(s.id) ? (
                              <button className="nav-item" style={{ padding: '8px', opacity: 0.3, cursor: 'not-allowed' }} title="Core — Lifecycle only">
                                <ShieldCheck size={18} />
                              </button>
                            ) : null}
                          </div>

                          {/* Inline drawers (Accordion) */}
                          {serverDrawer?.serverId === s.id && serverDrawer?.mode !== 'inspect' && (
                            <div className="glass-card" style={{ marginTop: '16px', background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(59,130,246,0.45)', animation: 'slideIn 0.2s ease-out' }}>
                              <div style={{ fontSize: '11px', fontWeight: 600, color: 'rgba(59,130,246,0.9)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span>
                                  {serverDrawer?.mode === 'log' ? 'Lifecycle Log' : 'Audit Report'}
                                </span>
                                <button className="nav-item" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => setServerDrawer(null)}>Close</button>
                              </div>
                              <pre style={{ margin: 0, padding: '12px', borderRadius: '10px', background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.08)', fontSize: '11px', whiteSpace: 'pre-wrap', maxHeight: '260px', overflow: 'auto', fontFamily: 'ui-monospace, Menlo, monospace', color: '#e2e8f0' }}>
                                {(() => {
                                  const key = `${s.id}:${serverDrawer?.mode || 'log'}`;
                                  const d = serverDrawerData[key];
                                  if (!d) return 'Loading...';
                                  if (d?.error) return String(d.error);
                                  if (serverDrawer?.mode === 'log') return ((d?.lines || []) as string[]).join('\n') || '(empty log)';
                                  return JSON.stringify(d, null, 2);
                                })()}
                              </pre>
                            </div>
                          )}

                          {serverDrawer?.serverId === s.id && serverDrawer?.mode === 'inspect' && (
                            <div className="glass-card" style={{ marginTop: '16px', background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(16,185,129,0.45)', animation: 'slideIn 0.2s ease-out' }}>
                              <div style={{ fontSize: '11px', fontWeight: 600, color: 'rgba(16,185,129,0.9)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span>Inspector</span>
                                <button className="nav-item" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => setServerDrawer(null)}>Close</button>
                              </div>
                              <pre style={{ margin: 0, padding: '12px', borderRadius: '10px', background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.08)', fontSize: '11px', whiteSpace: 'pre-wrap', maxHeight: '260px', overflow: 'auto', fontFamily: 'ui-monospace, Menlo, monospace', color: '#e2e8f0' }}>
                                {(() => {
                                  const key = `${s.id}:inspect`;
                                  const d = serverDrawerData[key] ?? s.raw;
                                  return JSON.stringify(d, null, 2);
                                })()}
                              </pre>
                            </div>
                          )}

                          {/* Inline Injection Drawer (Accordion) */}
                          {isInjecting && (
                            <div className="glass-card" style={{ marginTop: '16px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--primary)', animation: 'slideIn 0.2s ease-out' }}>
                              <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--primary)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                Target IDE
                              </div>
                              <div style={{ display: 'flex', gap: '8px' }}>
                                <select className="glass-card" style={{ flex: 1, padding: '8px', fontSize: '12px', background: 'rgba(255,255,255,0.05)' }} value={targetClient} onChange={e => setTargetClient(e.target.value)}>
                                  {availableClients.length > 0 ? (
                                    availableClients.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)
                                  ) : (
                                    <option value="" disabled>No supported IDEs found</option>
                                  )}
                                </select>
                                <button className="nav-item badge-primary" style={{ padding: '8px 16px', fontSize: '12px' }} onClick={() => {
                                  addNotification(`Injecting ${s.name} into ${targetClient}...`, 'info');
                                  const cmd = buildInjectionCommand(s, targetClient);
                                  if (!cmd) {
                                    addNotification("Injection failed: missing start command in inventory.", "error");
                                    return;
                                  }
                                  fetch(API_BASE + '/nexus/run', {
                                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ command: cmd })
                                  }).then(r => r.json()).then(d => {
                                    if (d.success) {
                                      addNotification("Injection successful.", "success");
                                      // Refresh status
                                      fetch(API_BASE + '/injector/status', {
                                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ server_id: s.id, name: s.name })
                                      }).then(r => r.json()).then(d => setInjectionStatus(d));
                                    } else {
                                      addNotification(d.stderr || d.error || "Injection failed", "error");
                                    }
                                  });
                                }}>
                                  Inject
                                </button>
                              </div>

                              <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                                <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginBottom: '4px' }}>CURRENT STATE</div>
                                {injectionStatus ? (
                                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                    {injectionStatus.injected_into?.length > 0 ? injectionStatus.injected_into.map((c: string) => (
                                      <span key={c} className="badge badge-success" style={{ fontSize: '10px' }}>{c}</span>
                                    )) : <span style={{ fontSize: '11px', fontStyle: 'italic', opacity: 0.6 }}>Not injected anywhere.</span>}
                                  </div>
                                ) : <span className="pulse-dot pulse-blue" style={{ width: 6, height: 6 }}></span>}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* List View */}
                {inventoryView === 'list' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                    {(systemStatus?.servers || []).map((s: any, idx: number) => (
                      <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 10px', borderBottom: '1px solid rgba(255,255,255,0.05)', background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)', borderLeft: `3px solid ${s.status === 'online' ? '#10b981' : '#ef4444'}`, transition: 'background 0.2s' }} className="table-row">
                        <div style={{ flex: 2, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                            {!['mcp-injector', 'mcp-server-manager', 'repo-mcp-packager', 'nexus-librarian'].includes(s.id) ? (
                              <button
                                className="nav-item"
                                style={{ padding: '3px 6px', color: 'var(--danger)' }}
                                onClick={() => {
                                  openConfirmPanel({
                                    title: `Remove "${s.name}" from inventory?`,
                                    danger: true,
                                    confirmLabel: 'Remove',
                                    details: `Server ID: ${s.id}`,
                                    onConfirm: async () => {
                                      const res = await fetch(API_BASE + '/server/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: s.id }) });
                                      if (res.ok) { addNotification(`Removed ${s.name}.`, 'success'); fetchData(); }
                                      else { const d = await res.json().catch(() => ({})); addNotification(d.error || 'Failed.', 'error'); }
                                    }
                                  });
                                }}
                                title="Remove"
                                aria-label="Remove"
                              >
                                <Trash2 size={12} />
                              </button>
                            ) : (
                              <span style={{ width: 28 }} />
                            )}
                            <b style={{ fontSize: '12px', display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.name}</b>
                          </div>
                          <small style={{ opacity: 0.45, fontSize: '9px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.raw?.path || s.id}</small>
                        </div>
                        <div style={{ flex: 1 }}>
                          <span style={{ fontSize: '9px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>{s.type || 'server'}</span>
                        </div>
                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flex: 1 }}>
                          {s.metrics?.pid && <span className="badge badge-dim" style={{ fontSize: '9px' }}>PID {s.metrics.pid}</span>}
                          {s.metrics?.cpu !== undefined && <span className="badge badge-dim" style={{ fontSize: '9px' }}>{s.metrics.cpu?.toFixed(1)}% CPU</span>}
                          {s.metrics?.ram !== undefined && <span className="badge badge-dim" style={{ fontSize: '9px' }}>{(s.metrics.ram / 1024 / 1024).toFixed(0)} MB</span>}
                        </div>
                        <span className={`badge ${s.status === 'online' ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: '10px', whiteSpace: 'nowrap' }}>{s.status}</span>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button
                            className={`nav-item ${s.status === 'online' ? 'badge-danger' : 'badge-primary'}`}
                            style={{ padding: '4px 10px', fontSize: '11px', opacity: pendingServerAction[s.id] ? 0.6 : 1 }}
                            disabled={!!pendingServerAction[s.id]}
                            onClick={() => handleControl(s.id, s.status === 'online' ? 'stop' : 'start')}
                            title={pendingServerAction[s.id] ? `Working: ${pendingServerAction[s.id]}` : undefined}
                          >
                            {pendingServerAction[s.id]
                              ? (pendingServerAction[s.id] === 'start' ? 'Starting…' : 'Stopping…')
                              : (s.status === 'online' ? 'Stop' : 'Start')}
                          </button>
                          <button className="nav-item" style={{ padding: '4px 6px' }} onClick={() => openServerDrawer(s.id, 'log')} title="View lifecycle log"><Terminal size={12} /></button>
                          <button className="nav-item" style={{ padding: '4px 6px' }} onClick={() => openServerDrawer(s.id, 'report')} title="Open audit report"><FileText size={12} /></button>
                          <button className="nav-item" style={{ padding: '4px 6px' }} onClick={() => openServerDrawer(s.id, 'inspect', s.raw)} title="Inspect"><Search size={12} /></button>
                          {!['mcp-injector', 'mcp-server-manager', 'repo-mcp-packager'].includes(s.id) ? (
                            <>
                              <button className="nav-item badge-command" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => {
                                setInjectTarget(s);
                                setInjectionStatus(null);
                                // Fetch clients first
                                fetch(API_BASE + '/injector/clients').then(r => r.json()).then(d => {
                                  setAvailableClients(d.clients || []);
                                  if (d.clients && d.clients.length > 0) setTargetClient(d.clients[0]);
                                });
                                fetch(API_BASE + '/injector/status', {
                                  method: 'POST', headers: { 'Content-Type': 'application/json' },
                                  body: JSON.stringify({ server_id: s.id, name: s.name })
                                }).then(r => r.json()).then(d => setInjectionStatus(d));
                              }} title="Inject"><Activity size={14} /></button>
                            </>
                          ) : (
                            <button className="nav-item" style={{ padding: '4px 8px', opacity: 0.3, cursor: 'not-allowed' }} title="Core"><ShieldCheck size={14} /></button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          )}

          {activeTab === 'librarian' && (
            <div className="tab-pane active" style={{ animation: 'fadeIn 0.3s ease-out' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '12px' }}>
                  Library Resources {watcherStatus === 'online' && <span className="pulse-dot pulse-green" style={{ display: 'inline-block' }}></span>}
                </h2>
                <div className="glass-card" style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
                  <Globe size={14} color="var(--primary)" />
                  <code>http://127.0.0.1:5001/mcp/sse</code>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '16px', marginBottom: '16px' }}>
                <section className="glass-card">
                  <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}><Search size={20} color="var(--primary)" /> Scan Roots</h3>
                  <p style={{ color: 'var(--text-dim)', fontSize: '13px', margin: '8px 0 20px' }}>
                    Register folders for indexing. This powers Librarian discovery without hard-coded paths.
                  </p>
                  <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
                    <input className="glass-card" style={{ flex: 1, padding: '12px 16px', background: 'rgba(0,0,0,0.3)' }} id="root-entry" placeholder="Absolute local path" />
                    <button className="nav-item" style={{ padding: '0 16px' }} onClick={async () => {
                      try {
                        const res = await fetch(API_BASE + '/os/pick_folder', { method: 'POST' });
                        const d = await res.json().catch(() => ({}));
                        if (!res.ok || !d.success) return addNotification(d.error || "Picker failed.", "error");
                        (document.getElementById('root-entry') as HTMLInputElement).value = d.path || '';
                      } catch (e) { addNotification(String(e), 'error'); }
                    }}>Browse…</button>
                    <button className="nav-item badge-success" style={{ padding: '0 24px' }} onClick={async () => {
                      const p = (document.getElementById('root-entry') as HTMLInputElement).value;
                      if (!p) return addNotification("Path cannot be empty.", "error");
                      const res = await fetch(API_BASE + '/librarian/roots', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: p }) });
                      if (res.ok) {
                        addNotification("Scan root added successfully.", "success");
                        (document.getElementById('root-entry') as HTMLInputElement).value = '';
                        fetchData();
                      } else {
                        const d = await res.json().catch(() => ({}));
                        addNotification(d.error || "Failed to add root.", "error");
                      }
                    }}>Add Root</button>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {scanRoots.map(r => (
                      <div key={r.id} className="table-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                        <code>{r.path}</code>
                        <X size={16} style={{ cursor: 'pointer', color: '#ef4444', opacity: 0.6 }} onClick={() => {
                          openConfirmPanel({
                            title: 'Remove scan root?',
                            danger: true,
                            confirmLabel: 'Remove',
                            details: `Root ID: ${r.id}\nPath: ${r.path}`,
                            onConfirm: async () => {
                              await fetch(`${API_BASE}/librarian/roots?id=${r.id}`, { method: 'DELETE' });
                              addNotification("Scan root removed.", "success");
                              fetchData();
                            }
                          });
                        }} />
                      </div>
                    ))}
                  </div>
                </section>

                <section className="glass-card">
                  <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}><Library size={20} color="var(--success)" /> Quick Index (File or URL)</h3>
                  <p style={{ color: 'var(--text-dim)', fontSize: '13px', margin: '8px 0 20px' }}>
                    Add a single file path or URL directly. Supports spaces and <code>~/</code> paths.
                  </p>
                  <div style={{ display: 'flex', gap: '12px' }}>
                    <input
                      className="glass-card"
                      style={{ flex: 1, padding: '12px 16px', background: 'rgba(0,0,0,0.3)' }}
                      value={quickIndexResource}
                      onChange={e => setQuickIndexResource(e.target.value)}
                      placeholder='e.g. "/Users/almowplay/developer/dropbox/ComplexEventProcessing Refined.pdf"'
                    />
                    <button className="nav-item" style={{ padding: '0 16px' }} onClick={async () => {
                      try {
                        const res = await fetch(API_BASE + '/os/pick_file', { method: 'POST' });
                        const d = await res.json().catch(() => ({}));
                        if (!res.ok || !d.success) return addNotification(d.error || "Picker failed.", "error");
                        setQuickIndexResource(d.path || '');
                      } catch (e) { addNotification(String(e), 'error'); }
                    }}>Pick File…</button>
                    <button className="nav-item badge-success" style={{ padding: '0 24px' }} onClick={async () => {
                      const r = quickIndexResource.trim();
                      if (!r) return addNotification("Resource cannot be empty.", "error");
                      addNotification("Indexing resource...", "info");
                      try {
                        const res = await fetch(API_BASE + '/librarian/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ resource: r }) });
                        const data = await res.json().catch(() => ({}));
                        if (!res.ok || data.success === false) {
                          addNotification(data.error || data.stderr || "Index failed.", "error");
                          return;
                        }
                        addNotification("Indexed successfully.", "success");
                        setLibrarianLastIndexed({ resource: r, when: Date.now() });
                        setQuickIndexResource('');
                        fetchData();
                      } catch (e) {
                        addNotification(String(e), "error");
                      }
                    }}>Index</button>
                  </div>
                </section>
              </div>

              {librarianLastIndexed && (
                <section className="glass-card" style={{ marginTop: '16px', border: '1px solid rgba(59,130,246,0.35)', background: 'rgba(0,0,0,0.18)' }}>
                  <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Activity size={18} color="var(--primary)" /> Next Steps
                  </h3>
                  <p style={{ color: 'var(--text-dim)', fontSize: '13px', margin: '8px 0 14px' }}>
                    Indexed: <code>{librarianLastIndexed.resource}</code>
                  </p>
                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    <button
                      className="nav-item badge-command"
                      style={{ padding: '10px 14px', fontSize: '12px' }}
                      onClick={() => {
                        // Treat Librarian as an injectable MCP server (even though it's a core component).
                        const s = (systemStatus?.servers || []).find((x: any) => x?.id === 'nexus-librarian') || { id: 'nexus-librarian', name: 'Nexus Librarian' };
                        setInjectTarget(s);
                        setInjectionStatus(null);
                        fetch(API_BASE + '/injector/clients').then(r => r.json()).then(d => {
                          setAvailableClients(d.clients || []);
                          if (d.clients && d.clients.length > 0) setTargetClient(d.clients[0]);
                        });
                        fetch(API_BASE + '/injector/status', {
                          method: 'POST', headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ server_id: 'nexus-librarian', name: 'Nexus Librarian' })
                        }).then(r => r.json()).then(d => setInjectionStatus(d));
                        // Bring user to a surface where Inject drawer is visible.
                        setActiveTab('dashboard');
                      }}
                      title="Inject Librarian into an IDE client so you can query the knowledge base from that client."
                    >
                      Inject Librarian into IDE
                    </button>

                    <button
                      className="nav-item"
                      style={{ padding: '10px 14px', fontSize: '12px' }}
                      onClick={() => {
                        openLogBrowser('audit', 'nexus-librarian');
                      }}
                      title="Open in-app raw diagnostics/report without leaving the GUI."
                    >
                      Open Log Browser
                    </button>

                    <button
                      className="nav-item"
                      style={{ padding: '10px 14px', fontSize: '12px' }}
                      onClick={() => setLibrarianLastIndexed(null)}
                      title="Dismiss this panel."
                    >
                      Dismiss
                    </button>
                  </div>
                </section>
              )}

              <div className="glass-card" style={{ padding: 0 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ textAlign: 'left', opacity: 0.6, fontSize: '11px', textTransform: 'uppercase', letterSpacing: '1px' }}>
                      <th style={{ padding: '16px' }}>Resource Name / URI</th>
                      <th style={{ padding: '16px' }}>Domain</th>
                      <th style={{ padding: '16px', textAlign: 'right' }}>Management</th>
                    </tr>
                  </thead>
                  <tbody>
                    {links.map(l => (
                      <tr key={l.id} className="table-row">
                        <td style={{ padding: '16px' }}>
                          <div style={{ fontWeight: 600 }}>{l.title}</div>
                          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>{l.url}</div>
                        </td>
                        <td style={{ padding: '16px' }}><span className="badge-info badge">{l.domain}</span></td>
                        <td style={{ padding: '16px', textAlign: 'right' }}>
                          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                            <button className="nav-item badge-info" style={{ padding: '6px 12px', fontSize: '11px' }} onClick={() => {
                              fetch(API_BASE + '/librarian/resource/open', {
                                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: l.id })
                              }).then(res => {
                                if (res.ok) addNotification("Opening resource...", "info");
                              });
                            }}>OPEN</button>

                            {l.url.startsWith('file://') && (
                              <button className="nav-item badge-secondary" style={{ padding: '6px 12px', fontSize: '11px' }} onClick={() => {
                                fetch(API_BASE + '/librarian/resource/edit', {
                                  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: l.id })
                                }).then(res => {
                                  if (res.ok) addNotification("Opening editor...", "info");
                                });
                              }}>EDIT</button>
                            )}

                            <button className="nav-item" style={{ border: 'none', color: '#ef4444', background: 'transparent', padding: '0 8px' }} onClick={() => {
                              openConfirmPanel({
                                title: `Delete "${l.title}" from knowledge base?`,
                                danger: true,
                                confirmLabel: 'Delete',
                                details: `Resource ID: ${l.id}\nURL: ${l.url}`,
                                onConfirm: async () => {
                                  const res = await fetch(API_BASE + '/librarian/resource/delete', {
                                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: l.id })
                                  });
                                  if (res.ok) {
                                    addNotification("Resource deleted.", "success");
                                    fetchData();
                                  } else {
                                    const d = await res.json().catch(() => ({}));
                                    addNotification(d.error || 'Delete failed.', "error");
                                  }
                                }
                              });
                            }} aria-label="Delete resource">
                              <Trash2 size={18} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {links.length === 0 && (
                      <tr>
                        <td colSpan={3} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-dim)' }}>
                          No resources indexed yet. Add scan roots above.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'terminal' && (
            <div className="tab-pane active" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 200px)', animation: 'slideRight 0.3s ease-out' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', marginBottom: '20px' }}>
                <div style={{ display: 'flex', gap: '8px', flex: 1 }}>
                  <div style={{ position: 'relative', flex: 1 }}>
                    <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', opacity: 0.5 }} />
                    <input
                      className="glass-card" style={{ width: '100%', padding: '12px 12px 12px 40px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--card-border)' }}
                      placeholder="Filter session timeline (commands, errors, thinking)..."
                      value={terminalFilter} onChange={e => setTerminalFilter(e.target.value)}
                    />
                  </div>
                  <select className="glass-card" style={{ padding: '0 16px', background: 'rgba(0,0,0,0.3)' }} value={terminalLevel} onChange={e => setTerminalLevel(e.target.value)}>
                    <option value="ALL">All Event Types</option>
                    <option value="COMMAND">Commands Only</option>
                    <option value="ERROR">Errors Only</option>
                    <option value="THINKING">Thinking Blocks</option>
                    <option value="INFO">Information</option>
                  </select>
                </div>
                <button className="nav-item badge-success" style={{ fontWeight: 600 }} onClick={() => {
                  addNotification("Opening audit report...", "info");
                  openLogBrowser('audit');
                }}>
                  <FileText size={18} /> Audit
                </button>
              </div>

              <div className="glass-card" style={{ flex: 1, overflowY: 'auto', padding: 0, background: 'rgba(0,0,0,0.2)', fontSize: '13px', display: 'flex', flexDirection: 'column' }}>
                {filteredLogs.map((log, i) => (
                  <div key={i} className="table-row" style={{ padding: '10px 20px' }}>
                    <div style={{ display: 'flex', gap: '16px', alignItems: 'center', cursor: 'pointer' }} onClick={() => setSelectedLogEntry(log)}>
                      <span style={{ fontSize: '11px', opacity: 0.4, minWidth: '80px', fontFamily: 'monospace' }}>{new Date(log.timestamp * 1000).toLocaleTimeString()}</span>
                      <span className={`badge badge-${(log.level || 'info').toLowerCase()}`} style={{ minWidth: '85px', textAlign: 'center', fontSize: '10px', fontWeight: 700 }}>{log.level}</span>
                      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: log.level === 'ERROR' ? 700 : 500, color: log.level === 'ERROR' ? '#ef4444' : log.level === 'COMMAND' ? '#3b82f6' : 'inherit' }}>{log.message}</span>
                        <button className="nav-item" style={{ padding: '4px', opacity: 0.5 }} onClick={(e) => {
                          e.stopPropagation();
                          navigator.clipboard.writeText(log.message || '');
                          addNotification("Text copied", "info");
                        }} title="Copy Text">
                          <Copy size={12} />
                        </button>
                      </div>
                      {log.metadata?.raw_result && (
                        <button
                          className="nav-item"
                          style={{ display: 'flex', alignItems: 'center', gap: '6px', opacity: 0.7, padding: '6px 8px', fontSize: '11px' }}
                          onClick={(e) => {
                            e.stopPropagation();
                            setExpandedLog(prev => (prev === i ? null : i));
                          }}
                          title="Toggle raw output"
                        >
                          <small style={{ fontSize: '10px' }}>{expandedLog === i ? 'HIDE' : 'VIEW'} OUTPUT</small>
                          {expandedLog === i ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </button>
                      )}
                    </div>
                    {expandedLog === i && log.metadata?.raw_result && (
                      <div style={{ marginTop: '12px', animation: 'slideIn 0.2s ease-out' }}>
                        <pre style={{ background: 'rgba(0,0,0,0.4)', padding: '16px', fontSize: '12px', borderRadius: '8px', overflowX: 'auto', whiteSpace: 'pre-wrap', fontFamily: 'monospace', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                          {log.metadata.raw_result}
                        </pre>
                      </div>
                    )}
                    {log.metadata?.tokens && log.metadata.tokens.total > 0 && (
                      <div className="badge" style={{
                        fontSize: '9px',
                        marginLeft: 'auto',
                        marginRight: '16px',
                        color: log.metadata.tokens.total > 10000 ? '#ef4444' : log.metadata.tokens.total > 1000 ? '#eab308' : '#10b981',
                        border: `1px solid ${log.metadata.tokens.total > 10000 ? 'rgba(239,68,68,0.3)' : log.metadata.tokens.total > 1000 ? 'rgba(234,179,8,0.3)' : 'rgba(16,185,129,0.3)'}`
                      }}>
                        {log.metadata.tokens.total} T
                      </div>
                    )}
                    {log.suggestion && <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginLeft: '197px', marginTop: '4px' }}>↳ {log.suggestion}</div>}
                  </div>
                ))}
                {filteredLogs.length === 0 && (
                  <div style={{ padding: '40px', textAlign: 'center', opacity: 0.5 }}>
                    No session activities found matching your criteria.
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'operations' && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px', animation: 'fadeIn 0.4s ease-out' }}>
              {commandCatalog.map(tool => (
                <section key={tool.id} className="glass-card" style={{ padding: '24px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                    <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <ShieldCheck size={20} color="var(--primary)" />
                      {tool.name}
                    </h3>
                    <button className="nav-item" style={{ padding: '6px' }} onClick={() => fetchHelp(tool.bin, tool.name)} title="View CLI Help">
                      <Info size={16} />
                    </button>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginBottom: '20px' }}>{tool.description}</p>
                  {tool.actions.map((act: any, idx: number) => {
                    const uniqueKey = `${tool.id}-${idx}`;
                    const cmdString = `${tool.bin} ${act.cmd} ${catalogInputs[uniqueKey] || ''}`.trim();

                    const isCustom = act.name === 'Custom Run';
                    const cardStyle = isCustom ? {
                      border: '1px solid rgba(168, 85, 247, 0.3)',
                      background: 'rgba(168, 85, 247, 0.05)'
                    } : {
                      border: '1px solid rgba(255,255,255,0.05)',
                      background: 'rgba(255,255,255,0.03)'
                    };

                    return (
                      <div key={idx} className="glass-card" style={{ padding: '16px', borderRadius: '12px', marginBottom: '16px', ...cardStyle }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ flex: 1 }}>
                            <b style={{ color: isCustom ? '#a855f7' : 'inherit' }}>{act.name}</b>
                            <br /><small style={{ opacity: 0.6, fontSize: '11px' }}>{act.desc}</small>
                          </div>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button className={`nav-item ${isCustom ? '' : 'badge-success'}`}
                              style={{ padding: '4px 12px', borderColor: isCustom ? '#a855f7' : undefined, color: isCustom ? '#a855f7' : undefined }}
                              onClick={() => handleRun(cmdString, uniqueKey)}>
                              RUN
                            </button>
                          </div>
                        </div>

                        {/* Universal Custom Args Field */}
                        <div style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
                          <input
                            className="glass-card" style={{ width: '100%', padding: '8px 12px', fontSize: '12px', background: 'rgba(0,0,0,0.2)' }}
                            placeholder={act.arg ? `Required: ${act.arg}` : "Optional arguments..."}
                            onChange={e => setCatalogInputs({ ...catalogInputs, [uniqueKey]: e.target.value })}
                            value={catalogInputs[uniqueKey] || ''}
                          />
                          <button className="nav-item" style={{ padding: '8px' }} onClick={() => {
                            navigator.clipboard.writeText(cmdString);
                            addNotification("Command copied to clipboard", "info");
                          }} title="Copy Command">
                            <Copy size={16} />
                          </button>
                        </div>

                        {/* Output Display */}
                        {opOutputs[uniqueKey] && (
                          <div style={{ marginTop: '12px', animation: 'slideIn 0.2s ease-out' }}>
                            <div style={{ fontSize: '10px', textTransform: 'uppercase', marginBottom: '4px', opacity: 0.7, display: 'flex', justifyContent: 'space-between' }}>
                              <span>Result ({opOutputs[uniqueKey].status})</span>
                              <span style={{ cursor: 'pointer' }} onClick={() => setOpOutputs(prev => { const n = { ...prev }; delete n[uniqueKey]; return n; })}>CLEAR</span>
                            </div>
                            <pre style={{
                              background: 'rgba(0,0,0,0.5)',
                              padding: '12px',
                              borderRadius: '8px',
                              fontSize: '11px',
                              fontFamily: 'monospace',
                              whiteSpace: 'pre-wrap',
                              maxHeight: '200px',
                              overflow: 'auto',
                              color: opOutputs[uniqueKey].status === 'error' ? '#ef4444' : '#10b981',
                              border: opOutputs[uniqueKey].status === 'error' ? '1px solid rgba(239,68,68,0.3)' : '1px solid rgba(16,185,129,0.3)'
                            }}>
                              {opOutputs[uniqueKey].output}
                            </pre>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </section>
              ))}
              {commandCatalog.length === 0 && (
                <div className="glass-card" style={{ gridColumn: '1/-1', textAlign: 'center', padding: '60px' }}>
                  <Activity size={48} style={{ opacity: 0.2, marginBottom: '16px' }} />
                  <h3>No Commands Discovered</h3>
                  <p style={{ color: 'var(--text-dim)' }}>Check backend catalog endpoint.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'forge' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', animation: 'fadeIn 0.4s ease-out' }}>
              <section className="glass-card" style={{ padding: '32px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
                  <Cpu size={32} color="var(--primary)" />
                  <div>
                    <h2 style={{ margin: 0 }}>Nexus Forge</h2>
                    <p style={{ color: 'var(--text-dim)', fontSize: '14px', margin: 0 }}>Transform any folder or repository into a hardened MCP server.</p>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <label style={{ fontSize: '13px', fontWeight: 600, opacity: 0.7 }}>Source Path or Git URL</label>
                    <div style={{ display: 'flex', gap: '10px' }}>
                      <input
                        className="glass-card"
                        style={{ flex: 1, padding: '14px 18px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--card-border)', color: 'var(--text-main)' }}
                        placeholder="e.g. /Users/name/my-tool or https://github.com/user/repo"
                        value={forgeSource}
                        onChange={e => setForgeSource(e.target.value)}
                        disabled={isForging}
                      />
                      <button
                        className="nav-item"
                        style={{ padding: '0 14px', borderColor: 'rgba(59,130,246,0.6)', color: '#3b82f6' }}
                        disabled={isForging}
                        onClick={async () => {
                          addNotification("Opening folder picker...", "info");
                          try {
                            const res = await fetch(API_BASE + '/os/pick_folder', { method: 'POST' });
                            const d = await res.json();
                            if (d?.success && d?.path) {
                              setForgeSource(d.path);
                              addNotification("Folder selected.", "success");
                            } else {
                              addNotification(d?.error || "Folder picker failed.", "error");
                            }
                          } catch (e) {
                            addNotification(String(e), "error");
                          }
                        }}
                      >
                        Browse…
                      </button>
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <label style={{ fontSize: '13px', fontWeight: 600, opacity: 0.7 }}>Server Name (Optional)</label>
                    <input
                      className="glass-card"
                      style={{ width: '100%', padding: '14px 18px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--card-border)', color: 'var(--text-main)' }}
                      placeholder="e.g. my-hardened-tool"
                      value={forgeName}
                      onChange={e => setForgeName(e.target.value)}
                      disabled={isForging}
                    />
                  </div>

                  {!isForging ? (
                    <button
                      className="nav-item badge-success"
                      style={{ width: '100%', padding: '16px', justifyContent: 'center', fontWeight: 700, fontSize: '16px', transition: 'all 0.3s' }}
                      onClick={async () => {
                        if (!forgeSource) return addNotification("Source is required.", "error");
                        setIsForging(true);
                        setForgeResult(null);
                        try {
                          const res = await fetch(API_BASE + '/forge', {
                            method: 'POST', headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ source: forgeSource, name: forgeName })
                          });
                          const data = await res.json();
                          if (data.task_id) {
                            addNotification("Forge task started. Monitoring...", "info");
                            const poll = setInterval(async () => {
                              const statusRes = await fetch(`${API_BASE}/forge/status/${data.task_id}`);
                              const statusData = await statusRes.json();

                              // Update logs in real-time
                              setForgeResult({
                                stdout: statusData.logs.join('\n'),
                                success: statusData.status === 'completed',
                                status: statusData.status,
                                server_path: statusData.result?.server_path
                              });

                              if (statusData.status === 'completed' || statusData.status === 'failed') {
                                clearInterval(poll);
                                setIsForging(false);
                                if (statusData.status === 'completed') {
                                  addNotification("Forge completed successfully!", "success");
                                  setForgeSource('');
                                  setForgeName('');
                                } else {
                                  addNotification("Forge failed.", "error");
                                }
                                fetchData();
                              }
                            }, 1000);
                          } else {
                            setIsForging(false);
                            addNotification(data.error || "Failed to start forge task", "error");
                          }
                        } catch (e) {
                          setIsForging(false);
                          addNotification(String(e), "error");
                        }
                      }}
                    >
                      FORGE MCP SERVER
                    </button>
                  ) : (
                    <div className="glass-card" style={{ padding: '20px', textAlign: 'center', background: 'rgba(16, 185, 129, 0.05)' }}>
                      <div className="pulse-dot pulse-green" style={{ margin: '0 auto 12px' }}></div>
                      <p style={{ fontSize: '14px', color: 'var(--primary)', fontWeight: 600 }}>Forging in Progress...</p>
                      <p style={{ fontSize: '12px', opacity: 0.7 }}>Streaming build logs from engine...</p>
                    </div>
                  )}
                </div>

                {forgeResult && (
                  <div style={{ marginTop: '24px', animation: 'slideIn 0.3s ease-out' }}>
                    <div className={`glass-card ${forgeResult.status === 'failed' ? 'badge-danger' : 'badge-success'}`} style={{ padding: '20px', background: forgeResult.status === 'failed' ? 'rgba(239, 68, 68, 0.05)' : 'rgba(16, 185, 129, 0.05)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                        {forgeResult.status === 'completed' ? <CheckCircle2 size={24} /> : forgeResult.status === 'failed' ? <AlertTriangle size={24} /> : <Activity size={24} className="spin" />}
                        <h3 style={{ margin: 0 }}>
                          {forgeResult.status === 'completed' ? 'Forge Successful' : forgeResult.status === 'failed' ? 'Forge Failed' : 'Build Log'}
                        </h3>
                      </div>

                      {forgeResult.status === 'completed' && forgeResult.server_path && (
                        <div style={{ marginBottom: '16px', padding: '12px', background: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}>
                          <strong>Inject Deployment</strong>
                          <p style={{ fontSize: '12px', opacity: 0.8, margin: '4px 0 12px' }}>
                            Your server is ready at <code>{forgeResult.server_path}</code>.
                          </p>

                          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
                            <label style={{ fontSize: '11px', fontWeight: 600, opacity: 0.7 }}>SELECT TARGET IDE</label>
                            <div style={{ display: 'flex', gap: '8px' }}>
                              <select
                                id="ide-selector"
                                className="glass-card"
                                style={{ flex: 1, padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--card-border)' }}
                                defaultValue="claude"
                              >
                                <option value="claude">Claude Desktop</option>
                                <option value="google-antigravity">Google AI Antigravity</option>
                                <option value="aistudio">Google AI Studio</option>
                                <option value="cursor">Cursor</option>
                                <option value="vscode">VS Code</option>
                                <option value="xcode">Xcode</option>
                              </select>
                              <button className="nav-item badge-success" onClick={async () => {
                                const clientName = (document.getElementById('ide-selector') as HTMLSelectElement).value;
                                const name = forgeResult.server_path.split('/').pop() || 'forged-server';
                                const scriptPath = `${forgeResult.server_path}/mcp_server.py`;

                                // Use mcp-surgeon which is whitelisted and points to the injector
                                const cmd = `mcp-surgeon --client ${clientName} --add --name "${name}" --command python3 --args "${scriptPath}"`;

                                openConfirmPanel({
                                  title: `Inject "${name}" into ${clientName}?`,
                                  confirmLabel: 'Inject',
                                  details: `Command:\n${cmd}`,
                                  onConfirm: async () => {
                                    handleRun(cmd, 'forge-inject');
                                  }
                                });
                              }}>INJECT NOW</button>
                            </div>
                            <div className="glass-card" style={{ padding: '12px', background: 'rgba(0,0,0,0.2)', fontSize: '11px', fontFamily: 'monospace', marginTop: '8px' }}>
                              <strong>Manual JSON Config:</strong><br />
                              <pre style={{ margin: '8px 0 0', opacity: 0.8, whiteSpace: 'pre-wrap' }}>{`"${forgeResult.server_path.split('/').pop() || 'forged-server'}": {\n  "command": "python3",\n  "args": ["${forgeResult.server_path}/mcp_server.py"]\n}`}</pre>
                            </div>
                          </div>
                        </div>
                      )}

                      <pre style={{
                        background: 'rgba(0,0,0,0.4)',
                        padding: '16px',
                        fontSize: '11px',
                        borderRadius: '8px',
                        overflow: 'auto',
                        maxHeight: '400px',
                        fontFamily: 'monospace',
                        color: forgeResult.status === 'failed' ? '#ef4444' : '#10b981',
                        whiteSpace: 'pre-wrap'
                      }}>
                        {forgeResult.stdout || 'Initializing...'}
                      </pre>
                    </div>
                  </div>
                )}
              </section>
            </div>
          )}

          {activeTab === 'lifecycle' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', animation: 'slideIn 0.3s ease-out' }}>
              <section className="glass-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
                  <div>
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}><Terminal size={20} color="#ef4444" /> Log Retention</h3>
                    <p style={{ color: 'var(--text-dim)', fontSize: '13px', margin: '8px 0 0' }}>
                      Prevents lifecycle logs from growing without bound (age + size cap).
                    </p>
                    <div style={{ marginTop: '10px', fontSize: '12px', opacity: 0.9 }}>
                      {(systemStatus as any)?.log_stats ? (
                        <>
                          <span style={{ fontWeight: 700 }}>{Math.round((((systemStatus as any).log_stats.bytes || 0) / (1024 * 1024)) * 10) / 10} MB</span>
                          <span style={{ opacity: 0.65 }}> • {(systemStatus as any).log_stats.files || 0} files</span>
                          <span style={{ opacity: 0.65 }}> • retention {(systemStatus as any).log_stats.retention_days}d</span>
                          <span style={{ opacity: 0.65 }}> • cap {(systemStatus as any).log_stats.max_mb}MB</span>
                        </>
                      ) : (
                        <span style={{ opacity: 0.7 }}>(no stats)</span>
                      )}
                    </div>
                  </div>
                  <button className="nav-item" style={{ padding: '8px 12px', fontSize: '12px' }} onClick={async () => {
                    try {
                      const res = await fetch(API_BASE + '/logs/prune', { method: 'POST' });
                      const d = await res.json().catch(() => ({}));
                      if (res.ok && d.success) {
                        addNotification('Logs pruned.', 'success');
                        fetchData();
                      } else {
                        addNotification(d.error || 'Log prune failed.', 'error');
                      }
                    } catch (e) {
                      addNotification(String(e), 'error');
                    }
                  }}>Prune Now</button>
                </div>
              </section>

              <section className="glass-card">
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}><Settings size={20} color="#3b82f6" /> Nexus Commander Lifecycle</h3>
                <p style={{ color: 'var(--text-dim)', fontSize: '13px', margin: '8px 0 0' }}>
                  Recovery, upgrades, snapshots, and reset. Indexing and scan roots live in Librarian.
                </p>
              </section>

              <section className="glass-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}><HardDrive size={20} color="#a855f7" /> State Snapshots</h3>
                    <p style={{ color: 'var(--text-dim)', fontSize: '13px', margin: '4px 0 0' }}>Auto-captures on change. Retains last 10 versions.</p>
                  </div>
                  <button className="nav-item" onClick={async () => {
                    addNotification("Capturing snapshot...", "info");
                    try {
                      await fetch(API_BASE + '/project/snapshot', { method: 'POST' });
                      addNotification("Snapshot captured successfully.", "success");
                      fetchData();
                    } catch (e) { addNotification(String(e), 'error'); }
                  }}>Capture Now</button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '20px' }}>
                  {inventoryHistory.length === 0 && <div style={{ opacity: 0.5, fontStyle: 'italic', padding: '20px', textAlign: 'center' }}>No snapshots found.</div>}

                  {inventoryHistory.map((h, i) => (
                    <div key={i} className="table-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <span style={{ fontSize: '24px', opacity: 0.1, fontWeight: 800, minWidth: '40px', textAlign: 'center' }}>#{i + 1}</span>
                        <div>
                          <b style={{ fontSize: '14px' }}>{h.name}</b>
                          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>Captured: {new Date(h.time * 1000).toLocaleString()}</div>
                        </div>
                      </div>
                      <button className="nav-item" style={{ border: '1px solid rgba(168, 85, 247, 0.4)', color: '#a855f7' }} onClick={() => {
                        openConfirmPanel({
                          title: 'Restore snapshot?',
                          danger: true,
                          confirmLabel: 'Restore',
                          details: `Snapshot: ${h.name}\nThis will overwrite current configuration.`,
                          onConfirm: async () => {
                            const res = await fetch(API_BASE + '/project/rollback', {
                              method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: h.name })
                            });
                            if (res.ok) {
                              addNotification("Rollback successful. System state restored.", "success");
                              fetchData();
                            } else {
                              const d = await res.json().catch(() => ({}));
                              addNotification(d.error || 'Rollback failed.', "error");
                            }
                          }
                        });
                      }}>Restore</button>
                    </div>
                  ))}
                </div>
              </section>

              {/* Update & Maintenance Section */}
              <section className="glass-card">
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}><Settings size={20} color="#3b82f6" /> System Maintenance</h3>
                <p style={{ color: 'var(--text-dim)', fontSize: '13px', margin: '8px 0 20px' }}>Manage core component versions and dependencies.</p>

                <div style={{ display: 'flex', gap: '16px', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '15px' }}>Nexus Suite</h4>
                      <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--text-dim)' }}>Core GUI, Bridge, and CLI tools</p>
                    </div>
                    <button className="nav-item" style={{ borderColor: '#3b82f6', color: '#3b82f6' }} onClick={async () => {
                      addNotification("Initiating Suite Update...", "info");
                      try {
                        const res = await fetch(API_BASE + '/system/update/nexus', { method: 'POST' });
                        const d = await res.json();
                        addNotification(d.message || d.error, d.success ? "success" : "error");
                      } catch (e) { addNotification(String(e), 'error'); }
                    }}>
                      Pull & Update
                    </button>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '15px' }}>Python Environment</h4>
                      <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--text-dim)' }}>Nexus Commander Python environment (this running process only)</p>
                    </div>
                    <button className="nav-item" style={{ borderColor: '#eab308', color: '#eab308' }} onClick={async () => {
                      addNotification("Upgrading Nexus Commander pip...", "info");
                      try {
                        const res = await fetch(API_BASE + '/system/update/python', { method: 'POST' });
                        const d = await res.json();
                        addNotification(d.message || d.error, d.success ? "success" : "error");
                      } catch (e) { addNotification(String(e), 'error'); }
                    }}>
                      Upgrade Nexus Commander Pip
                    </button>
                  </div>

                  {pythonInfo && (
                    <div className="glass-card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <h4 style={{ margin: 0, fontSize: '13px', opacity: 0.9 }}>Runtime Visibility</h4>
                          <p style={{ margin: '6px 0 0', fontSize: '11px', color: 'var(--text-dim)' }}>
                            Commander Python: <code>{pythonInfo.bridge?.python_version || 'unknown'}</code>
                          </p>
                        </div>
                        <button className="nav-item" style={{ padding: '6px 10px' }} onClick={() => fetchData()}>Refresh</button>
                      </div>

                      <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div style={{ fontSize: '11px' }}>
                          <div style={{ opacity: 0.7, marginBottom: '4px' }}>Bridge Interpreter</div>
                          <code style={{ fontSize: '10px' }}>{pythonInfo.bridge?.python || ''}</code>
                        </div>
                        <div style={{ fontSize: '11px' }}>
                          <div style={{ opacity: 0.7, marginBottom: '4px' }}>Commander Pip</div>
                          <code style={{ fontSize: '10px' }}>{pythonInfo.bridge?.pip_version || ''}</code>
                        </div>
                        <div style={{ fontSize: '11px' }}>
                          <div style={{ opacity: 0.7, marginBottom: '4px' }}>System python3</div>
                          <code style={{ fontSize: '10px' }}>{pythonInfo.system?.python3 || ''}</code>
                        </div>
                        <div style={{ fontSize: '11px' }}>
                          <div style={{ opacity: 0.7, marginBottom: '4px' }}>Nexus venv</div>
                          <code style={{ fontSize: '10px' }}>
                            {pythonInfo.nexus?.venv_exists ? 'present' : 'missing'} — {pythonInfo.nexus?.venv_python || ''}
                          </code>
                        </div>
                      </div>

                      <div style={{ marginTop: '12px', fontSize: '11px', opacity: 0.8 }}>Key Packages</div>
                      <div style={{ marginTop: '8px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '8px' }}>
                        {Object.entries(pythonInfo.packages || {}).map(([name, meta]: any) => (
                          <div key={name} className="glass-card" style={{ padding: '10px', background: 'rgba(0,0,0,0.25)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <b style={{ fontSize: '11px' }}>{name}</b>
                              <span className={`badge ${meta?.present ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: '9px' }}>
                                {meta?.present ? 'ok' : 'missing'}
                              </span>
                            </div>
                            <div style={{ marginTop: '6px', fontSize: '10px', opacity: 0.85 }}>
                              {meta?.version ? <code>{meta.version}</code> : <span style={{ opacity: 0.7 }}>—</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </section>

              <div className="glass-card" style={{ border: '1px solid #ef4444', background: 'rgba(239, 68, 68, 0.05)', padding: '24px' }}>
                <h3 style={{ color: '#ef4444', marginBottom: '8px' }}>Critical Maintenance</h3>
                <p style={{ fontSize: '13px', color: 'var(--text-dim)', marginBottom: '24px' }}>
                  Factory Reset is guided. Default is a safe environment reset; full wipe is optional.
                </p>
                <button
                  className="nav-item"
                  style={{ borderColor: '#ef4444', color: '#ef4444', width: '100%', padding: '14px', fontWeight: 700 }}
                  onClick={() => {
                    setPurgeConfirmText("");
                    setPurgePreview(null);
                    setPurgeModalOpen(true);
                  }}
                >
                  PURGE / FACTORY RESET…
                </button>
              </div>
            </div>
          )}
        </main>

        {/* True side panel — sibling of main, slides in from the right */}
        <div className={`metric-side-panel ${metricPanelOpen ? 'open' : ''}`}>
          <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--card-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              {(['cpu', 'ram', 'disk', 'health'] as const).map(m => (
                <button key={m} onClick={() => openMetricPanel(m)} style={{ padding: '6px 12px', borderRadius: '8px', border: 'none', cursor: 'pointer', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', background: selectedMetric === m ? 'rgba(59,130,246,0.25)' : 'rgba(255,255,255,0.05)', color: selectedMetric === m ? 'var(--primary)' : 'var(--text-dim)', transition: 'all 0.2s', letterSpacing: '0.5px' }}>
                  {m === 'cpu' ? 'CPU' : m === 'ram' ? 'RAM' : m === 'disk' ? 'Disk' : 'Health'}
                </button>
              ))}
            </div>
            <button className="nav-item" onClick={closeMetricPanel} style={{ padding: '6px', borderRadius: '50%' }}>
              <X size={16} />
            </button>
          </div>
          <div style={{ padding: '16px 0 0', overflowY: 'auto', flex: 1 }}>
            <div style={{ padding: '0 24px 12px', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-dim)', opacity: 0.6 }}>
              {selectedMetric === 'cpu' ? 'Processor Usage' : selectedMetric === 'ram' ? 'Memory Usage' : selectedMetric === 'disk' ? 'Disk Allocation' : 'Fleet Status'} — per server
            </div>
            {selectedMetric && (systemStatus?.servers || []).length === 0 && (
              <div style={{ opacity: 0.5, textAlign: 'center', padding: '40px 20px' }}>No active servers to report.</div>
            )}
            {selectedMetric && [...(systemStatus?.servers || [])].sort((a: any, b: any) => {
              if (selectedMetric === 'cpu') return (b.metrics?.cpu || 0) - (a.metrics?.cpu || 0);
              if (selectedMetric === 'ram') return (b.metrics?.ram || 0) - (a.metrics?.ram || 0);
              return 0;
            }).map((s: any) => (
              <div key={s.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 24px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <div style={{ minWidth: 0 }}>
                  <b style={{ display: 'block', fontSize: '13px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.name}</b>
                  <small style={{ opacity: 0.4, fontSize: '10px' }}>{s.id}</small>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  {selectedMetric === 'cpu' && <span className="badge badge-dim" style={{ background: (s.metrics?.cpu || 0) > 10 ? 'rgba(239,68,68,0.15)' : undefined, color: (s.metrics?.cpu || 0) > 10 ? '#ef4444' : undefined }}>{s.metrics?.cpu?.toFixed(1) || '0.0'}%</span>}
                  {selectedMetric === 'ram' && <span className="badge badge-dim">{((s.metrics?.ram || 0) / 1024 / 1024).toFixed(0)} MB</span>}
                  {selectedMetric === 'disk' && <span className="badge badge-dim" style={{ opacity: 0.4 }}>—</span>}
                  {selectedMetric === 'health' && <span className={`badge ${s.status === 'online' ? 'badge-success' : 'badge-danger'}`}>{s.status || 'unknown'}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div> {/* end content wrapper */}
    </div>
  );
};

export default App;
