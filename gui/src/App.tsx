import React, { useState, useEffect, useMemo, useCallback } from 'react';
import Sparkline from './components/Sparkline';
import {
  Activity, ShieldCheck, Settings,
  LayoutDashboard, Search, Cpu, Monitor,
  HardDrive, Globe, AlertTriangle, X, Trash2,
  FileText, Library, Terminal,
  ChevronDown, ChevronUp, CheckCircle2, Info, Copy
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
  const [inventoryHistory, setInventoryHistory] = useState<any[]>([]);
  const [commandCatalog, setCommandCatalog] = useState<any[]>([]);
  const [catalogInputs, setCatalogInputs] = useState<any>({});
  const [quickIndexResource, setQuickIndexResource] = useState<string>('');
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
        ['forge/last', (d) => d && Object.keys(d).length > 0 && setForgeResult({ ...d, status: 'completed' })]
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

  // Modal auto-close on tab change
  useEffect(() => {
    setSelectedItem(null);
  }, [activeTab]);

  const handleControl = async (id: string, action: string) => {
    try {
      addNotification(`Sending ${action} command to ${id}...`, 'info');
      const res = await fetch(API_BASE + '/server/control', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, action })
      });
      if (res.ok) {
        addNotification(`Server ${id} ${action} successful.`, 'success');
      } else {
        const data = await res.json();
        addNotification(data.error || `Failed to ${action} server.`, 'error');
      }
      fetchData();
    } catch (e) { addNotification(String(e), 'error'); }
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

      {selectedItem && (
        <div className="inspector-overlay" onClick={() => setSelectedItem(null)} style={{ background: 'rgba(0,0,0,0.7)', zIndex: 2000 }}>
          <div className="glass-card" onClick={e => e.stopPropagation()} style={{ width: '90%', maxWidth: '900px', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '20px', borderBottom: '1px solid var(--card-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <ShieldCheck size={24} color="var(--primary)" />
                <h3 style={{ margin: 0 }}>System Inspector</h3>
              </div>
              <button className="nav-item" onClick={() => setSelectedItem(null)} style={{ padding: '8px', borderRadius: '50%' }} aria-label="Close">
                <X size={20} />
              </button>
            </div>
            <pre style={{ padding: '24px', overflow: 'auto', background: 'rgba(0,0,0,0.4)', flex: 1, margin: 0, fontFamily: 'monospace', fontSize: '13px', color: '#10b981' }}>
              {JSON.stringify(selectedItem, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {helpContent && (
        <div className="inspector-overlay" onClick={() => setHelpContent(null)} style={{ background: 'rgba(0,0,0,0.5)', zIndex: 3000, justifyContent: 'flex-end', alignItems: 'flex-end' }}>
          <div className="glass-card" onClick={e => e.stopPropagation()} style={{
            width: '500px', height: '100vh',
            borderLeft: '1px solid var(--primary)',
            background: 'rgba(10, 10, 20, 0.95)',
            display: 'flex', flexDirection: 'column',
            animation: 'slideInRight 0.3s ease-out',
            borderRadius: '0'
          }}>
            <div style={{ padding: '20px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Info size={18} /> {helpTitle} Help
              </h3>
              <X size={20} style={{ cursor: 'pointer' }} onClick={() => setHelpContent(null)} />
            </div>
            <pre style={{
              padding: '20px', overflow: 'auto', flex: 1,
              fontFamily: 'monospace', fontSize: '11px',
              color: '#e2e8f0', whiteSpace: 'pre-wrap'
            }}>
              {helpContent}
            </pre>
          </div>
        </div>
      )}

      <aside className="sidebar">
        <div className="brand" style={{ cursor: 'pointer' }} onClick={() => setActiveTab('dashboard')}><ShieldCheck size={32} /> <span>Nexus</span></div>
        <nav className="nav-group">
          <div className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}><LayoutDashboard size={20} /> Dashboard</div>
          <div className={`nav-item ${activeTab === 'librarian' ? 'active' : ''}`} onClick={() => setActiveTab('librarian')}><Library size={20} /> Librarian</div>
          <div className={`nav-item ${activeTab === 'operations' ? 'active' : ''}`} onClick={() => setActiveTab('operations')} style={{ position: 'relative' }}>
            <Activity size={20} /> Operations
            {healthIssues.some(h => h.status === 'fatal' || h.status === 'error') && (
              <span className="pulse-dot pulse-red" style={{ position: 'absolute', top: 12, right: 12, width: 6, height: 6 }}></span>
            )}
          </div>
          <div className={`nav-item ${activeTab === 'terminal' ? 'active' : ''}`} onClick={() => setActiveTab('terminal')}><Terminal size={20} /> Command Hub</div>
          <div className={`nav-item ${activeTab === 'forge' ? 'active' : ''}`} onClick={() => setActiveTab('forge')}><Cpu size={20} /> Forge Engine</div>
        </nav>
        <div style={{ marginTop: 'auto' }} className="nav-group">
          <div className={`nav-item ${activeTab === 'lifecycle' ? 'active' : ''}`} onClick={() => setActiveTab('lifecycle')} style={{ position: 'relative' }}>
            <Settings size={20} /> Lifecycle
            {systemStatus?.updateAvailable && (
              <span className="pulse-dot pulse-blue" style={{ position: 'absolute', top: 12, right: 12, width: 6, height: 6 }}></span>
            )}
          </div>
        </div>

        <div style={{ marginTop: 'auto', padding: '0 16px', fontSize: '10px', color: 'var(--text-dim)', opacity: 0.5, letterSpacing: '0.5px' }}>
          CORE v{systemStatus?.version || '0.0.0'}
        </div>
      </aside>



      {/* Content area: main + metric side panel side-by-side */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' }}>
        <main className="main-viewport" style={{ flex: 1, overflow: 'hidden auto' }}>
          <header style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '32px', alignItems: 'center' }}>
            <div>
              <h1 style={{ fontSize: '28px', background: 'linear-gradient(90deg, #fff, var(--text-dim))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Workforce Nexus</h1>
              <p style={{ color: 'var(--text-dim)', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                {systemStatus?.posture || 'Disconnected'}
                <span className={`pulse-dot pulse-${systemStatus?.pulse || 'red'}`}></span>
              </p>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
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
                  <span style={{ fontSize: '26px', fontWeight: 700, margin: '12px 0 4px', display: 'block' }}>{systemStatus?.pulse === 'green' ? 'Stable' : 'Unstable'}</span>
                  <p style={{ color: 'var(--text-dim)', fontSize: '12px', margin: 0 }}>Fleet Health</p>
                </div>
              </div>

              <section className="glass-card" style={{ padding: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <h3 style={{ margin: 0, display: 'flex', gap: '10px', alignItems: 'center' }}><ShieldCheck size={18} /> Core Components</h3>
                  <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Always visible</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                  {Object.entries(systemStatus?.core_components || {}).map(([k, v]) => (
                    <div key={k} className="glass-card" style={{ padding: '12px', background: 'rgba(255,255,255,0.03)' }}>
                      <div style={{ fontSize: '11px', letterSpacing: '0.5px', textTransform: 'uppercase', color: 'var(--text-dim)' }}>{k.replace(/_/g, ' ')}</div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
                        <span style={{ fontWeight: 600 }}>{String(v)}</span>
                        <span className={`pulse-dot pulse-${v === 'online' ? 'green' : v === 'stopped' ? 'yellow' : 'red'}`} style={{ width: 6, height: 6 }}></span>
                      </div>
                    </div>
                  ))}
                </div>
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
                            <div style={{ wordBreak: 'break-all' }}>
                              <b style={{ fontSize: '16px' }}>{s.name}</b>
                              <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '4px' }}>TYPE: {(s.type || 'server').toUpperCase()}</div>
                              <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px', opacity: 0.7 }}>{s.raw?.path || s.id}</div>
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
                            <button className={`nav-item ${s.status === 'online' ? 'badge-danger' : 'badge-success'}`} style={{ flex: 1, justifyContent: 'center', fontSize: '12px' }} onClick={() => handleControl(s.id, s.status === 'online' ? 'stop' : 'start')}>
                              {s.status === 'online' ? 'Stop' : 'Start'}
                            </button>

                            {/* Audit Button (New Outcome) */}
                            <button className="nav-item" style={{ padding: '8px' }} onClick={() => window.open(`${API_BASE}/export/report?server=${s.id}`, '_blank')} title="Audit Log">
                              <FileText size={18} />
                            </button>

                            {/* Last Start Log */}
                            <button className="nav-item" style={{ padding: '8px' }} onClick={() => window.open(`${API_BASE}/server/logs/${s.id}/view`, '_blank')} title="View last start log">
                              <Terminal size={18} />
                            </button>

                            <button className="nav-item" style={{ padding: '8px' }} onClick={() => setSelectedItem(s.raw)} title="Inspect">
                              <Search size={18} />
                            </button>

                            {!['mcp-injector', 'mcp-server-manager', 'repo-mcp-packager', 'nexus-librarian'].includes(s.id) ? (
                              <>
                                <button className="nav-item" style={{ padding: '8px', color: 'var(--danger)' }} onClick={async () => {
                                  if (confirm(`Remove '${s.name}' from inventory?`)) {
                                    const res = await fetch(API_BASE + '/server/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: s.id }) });
                                    if (res.ok) { addNotification(`Removed ${s.name}.`, 'success'); fetchData(); }
                                    else { const d = await res.json(); addNotification(d.error || 'Failed.', 'error'); }
                                  }
                                }} title="Remove">
                                  <Trash2 size={18} />
                                </button>

                                <button className={`nav-item ${isInjecting ? 'active' : 'badge-command'}`} style={{ padding: '6px 12px', fontSize: '11px', display: 'flex', gap: '6px', alignItems: 'center' }} onClick={() => {
                                  if (isInjecting) {
                                    setInjectTarget(null); // Close drawer
                                  } else {
                                    setInjectTarget(s);
                                    setInjectionStatus(null);
                                    // Fetch clients
                                    fetch(API_BASE + '/injector/clients').then(r => r.json()).then(d => {
                                      setAvailableClients(d.clients || []);
                                      if (d.clients && d.clients.length > 0) setTargetClient(d.clients[0]);
                                    });
                                    // Fetch status
                                    fetch(API_BASE + '/injector/status', {
                                      method: 'POST', headers: { 'Content-Type': 'application/json' },
                                      body: JSON.stringify({ server_id: s.id, name: s.name })
                                    }).then(r => r.json()).then(d => setInjectionStatus(d));
                                  }
                                }} title="Inject to IDE">
                                  <Activity size={12} /> {isInjecting ? 'Close' : 'Inject'}
                                </button>
                              </>
                            ) : (
                              <button className="nav-item" style={{ padding: '8px', opacity: 0.3, cursor: 'not-allowed' }} title="Core — Lifecycle only">
                                <ShieldCheck size={18} />
                              </button>
                            )}
                          </div>

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
                                  fetch(API_BASE + '/nexus/run', {
                                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ command: `mcp-surgeon --add ${s.name} --client ${targetClient}` })
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
                      <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.05)', background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)', borderLeft: `3px solid ${s.status === 'online' ? '#10b981' : '#ef4444'}`, transition: 'background 0.2s' }} className="table-row">
                        <div style={{ flex: 2, minWidth: 0 }}>
                          <b style={{ fontSize: '14px', display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.name}</b>
                          <small style={{ opacity: 0.45, fontSize: '11px' }}>{s.raw?.path || s.id}</small>
                        </div>
                        <div style={{ flex: 1 }}>
                          <span style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>{s.type || 'server'}</span>
                        </div>
                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flex: 1 }}>
                          {s.metrics?.pid && <span className="badge badge-dim" style={{ fontSize: '9px' }}>PID {s.metrics.pid}</span>}
                          {s.metrics?.cpu !== undefined && <span className="badge badge-dim" style={{ fontSize: '9px' }}>{s.metrics.cpu?.toFixed(1)}% CPU</span>}
                          {s.metrics?.ram !== undefined && <span className="badge badge-dim" style={{ fontSize: '9px' }}>{(s.metrics.ram / 1024 / 1024).toFixed(0)} MB</span>}
                        </div>
                        <span className={`badge ${s.status === 'online' ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: '10px', whiteSpace: 'nowrap' }}>{s.status}</span>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button className={`nav-item ${s.status === 'online' ? 'badge-danger' : 'badge-success'}`} style={{ padding: '4px 12px', fontSize: '11px' }} onClick={() => handleControl(s.id, s.status === 'online' ? 'stop' : 'start')}>
                            {s.status === 'online' ? 'Stop' : 'Start'}
                          </button>
                          <button className="nav-item" style={{ padding: '4px 8px' }} onClick={() => setSelectedItem(s.raw)} title="Inspect"><Search size={14} /></button>
                          {!['mcp-injector', 'mcp-server-manager', 'repo-mcp-packager', 'nexus-librarian'].includes(s.id) ? (
                            <>
                              <button className="nav-item" style={{ padding: '4px 8px', color: 'var(--danger)' }} onClick={async () => {
                                if (confirm(`Remove '${s.name}'?`)) {
                                  const res = await fetch(API_BASE + '/server/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: s.id }) });
                                  if (res.ok) { addNotification(`Removed ${s.name}.`, 'success'); fetchData(); }
                                }
                              }} title="Remove"><Trash2 size={14} /></button>
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
                              if (confirm(`Are you sure you want to delete "${l.title}" from the knowledge base?`)) {
                                fetch(API_BASE + '/librarian/resource/delete', {
                                  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: l.id })
                                }).then(res => {
                                  if (res.ok) {
                                    addNotification("Resource deleted.", "success");
                                    fetchData();
                                  }
                                });
                              }
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
                          No resources indexed yet. Add scan roots in Lifecycle.
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
                  addNotification("Opening standard health report...", "info");
                  window.open(API_BASE + '/export/report', '_blank');
                }}>
                  <FileText size={18} /> Audit
                </button>
              </div>

              <div className="glass-card" style={{ flex: 1, overflowY: 'auto', padding: 0, background: 'rgba(0,0,0,0.2)', fontSize: '13px', display: 'flex', flexDirection: 'column' }}>
                {filteredLogs.map((log, i) => (
                  <div key={i} className="table-row" style={{ padding: '10px 20px' }}>
                    <div style={{ display: 'flex', gap: '16px', alignItems: 'center', cursor: 'pointer' }} onClick={() => setExpandedLog(expandedLog === i ? null : i)}>
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
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', opacity: 0.6 }}>
                          <small style={{ fontSize: '10px' }}>{expandedLog === i ? 'HIDE' : 'VIEW'} OUTPUT</small>
                          {expandedLog === i ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </div>
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
                    <input
                      className="glass-card"
                      style={{ width: '100%', padding: '14px 18px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--card-border)', color: 'var(--text-main)' }}
                      placeholder="e.g. /Users/name/my-tool or https://github.com/user/repo"
                      value={forgeSource}
                      onChange={e => setForgeSource(e.target.value)}
                      disabled={isForging}
                    />
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

                                if (confirm(`Inject "${name}" into ${clientName}?\n\nCommand: ${cmd}`)) {
                                  handleRun(cmd, 'forge-inject');
                                }
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
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}><Search size={20} color="var(--primary)" /> Scan Integration</h3>
                <p style={{ color: 'var(--text-dim)', fontSize: '13px', margin: '8px 0 20px' }}>Registered scan roots are indexed by the Nexus Librarian.</p>
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
                    }
                  }}>Add Path</button>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {scanRoots.map(r => (
                    <div key={r.id} className="table-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                      <code>{r.path}</code>
                      <X size={16} style={{ cursor: 'pointer', color: '#ef4444', opacity: 0.6 }} onClick={() => {
                        if (confirm("Remove this scan root?")) {
                          fetch(`${API_BASE}/librarian/roots?id=${r.id}`, { method: 'DELETE' }).then(() => {
                            addNotification("Scan root removed.", "success");
                            fetchData();
                          });
                        }
                      }} />
                    </div>
                  ))}
                </div>
              </section>

              <section className="glass-card">
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}><Library size={20} color="var(--success)" /> Quick Index (File or URL)</h3>
                <p style={{ color: 'var(--text-dim)', fontSize: '13px', margin: '8px 0 20px' }}>
                  Paste a local file path or URL. Supports spaces and <code>~/</code> paths.
                </p>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <input
                    className="glass-card"
                    style={{ flex: 1, padding: '12px 16px', background: 'rgba(0,0,0,0.3)' }}
                    value={quickIndexResource}
                    onChange={e => setQuickIndexResource(e.target.value)}
                    placeholder='e.g. "~/developer/dropbox/ComplexEventProcessing Refined.pdf"'
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
                      setQuickIndexResource('');
                      fetchData();
                    } catch (e) {
                      addNotification(String(e), "error");
                    }
                  }}>Index</button>
                </div>
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
                        if (confirm("DANGER: Rollback will overwrite current configuration. Proceed?")) {
                          fetch(API_BASE + '/project/rollback', {
                            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: h.name })
                          }).then(res => {
                            if (res.ok) {
                              addNotification("Rollback successful. System state restored.", "success");
                              fetchData();
                            }
                          });
                        }
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
                      <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--text-dim)' }}>Pip dependencies and runtime libs</p>
                    </div>
                    <button className="nav-item" style={{ borderColor: '#eab308', color: '#eab308' }} onClick={async () => {
                      addNotification("Upgrading Python packages...", "info");
                      try {
                        const res = await fetch(API_BASE + '/system/update/python', { method: 'POST' });
                        const d = await res.json();
                        addNotification(d.message || d.error, d.success ? "success" : "error");
                      } catch (e) { addNotification(String(e), 'error'); }
                    }}>
                      Upgrade Pip Deps
                    </button>
                  </div>
                </div>
              </section>

              <div className="glass-card" style={{ border: '1px solid #ef4444', background: 'rgba(239, 68, 68, 0.05)', padding: '24px' }}>
                <h3 style={{ color: '#ef4444', marginBottom: '8px' }}>Critical Maintenance</h3>
                <p style={{ fontSize: '13px', color: 'var(--text-dim)', marginBottom: '24px' }}>FACTORY RESET: This action will permanently remove all Nexus binaries and data.</p>
                <button className="nav-item" style={{ borderColor: '#ef4444', color: '#ef4444', width: '100%', padding: '14px', fontWeight: 700 }} onClick={() => {
                  if (confirm("UNINSTALL everything?")) {
                    addNotification("Uninstall sequence started...", "error");
                    fetch(API_BASE + '/system/uninstall', { method: 'POST' }).then(res => {
                      if (res.ok) window.location.reload();
                    });
                  }
                }}>PURGE ENTIRE SUITE</button>
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
