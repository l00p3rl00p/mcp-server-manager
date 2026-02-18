import React, { useState, useEffect, useMemo, useCallback } from 'react';
import Sparkline from './components/Sparkline';
import {
  Activity, ShieldCheck, Settings,
  LayoutDashboard, Search, Cpu, Monitor,
  HardDrive, Globe, AlertTriangle, X, Trash2,
  FileText, Library, Terminal,
  ChevronDown, ChevronUp, CheckCircle2, Info
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

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedItem, setSelectedItem] = useState<any>(null);
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
        ['nexus/catalog', setCommandCatalog]
      ];

      await Promise.all(endpoints.map(async ([path, setter]) => {
        try {
          const res = await fetch(`http://127.0.0.1:5001/${path}`);
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
      const res = await fetch('http://127.0.0.1:5001/server/control', {
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

  const filteredLogs = useMemo(() => {
    return logs.filter(l => {
      const msg = l.message || '';
      const sug = l.suggestion || '';
      const matchText = (msg + sug).toLowerCase().includes(terminalFilter.toLowerCase());
      const matchLevel = terminalLevel === 'ALL' || l.level === terminalLevel;
      return matchText && matchLevel;
    }).slice(-100).reverse();
  }, [logs, terminalFilter, terminalLevel]);

  const handleRun = async (cmd: string) => {
    try {
      addNotification(`Executing: ${cmd.split(' ')[0]}...`, 'info');
      const res = await fetch('http://127.0.0.1:5001/nexus/run', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
      });
      const data = await res.json();
      if (data.success) {
        addNotification("Operation completed successfully.", "success");
      } else {
        addNotification(`Operation failed: ${data.stderr || data.error}`, "error");
      }
      fetchData();
    } catch (e) { addNotification(String(e), "error"); }
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

      <aside className="sidebar">
        <div className="brand" style={{ cursor: 'pointer' }} onClick={() => setActiveTab('dashboard')}><ShieldCheck size={32} /> <span>Nexus</span></div>
        <nav className="nav-group">
          <div className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}><LayoutDashboard size={20} /> Dashboard</div>
          <div className={`nav-item ${activeTab === 'librarian' ? 'active' : ''}`} onClick={() => setActiveTab('librarian')}><Library size={20} /> Librarian</div>
          <div className={`nav-item ${activeTab === 'terminal' ? 'active' : ''}`} onClick={() => setActiveTab('terminal')}><Terminal size={20} /> Command Hub</div>
          <div className={`nav-item ${activeTab === 'operations' ? 'active' : ''}`} onClick={() => setActiveTab('operations')}><Activity size={20} /> Operations</div>
        </nav>
        <div style={{ marginTop: 'auto' }} className="nav-group">
          <div className={`nav-item ${activeTab === 'lifecycle' ? 'active' : ''}`} onClick={() => setActiveTab('lifecycle')}><Settings size={20} /> Lifecycle</div>
        </div>
      </aside>

      <main className="main-viewport">
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
                fetch('http://127.0.0.1:5001/nexus/projects', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: p.id, path: p.path }) }).then(() => {
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
            {healthIssues.length > 0 && (
              <section className="glass-card" style={{ border: '1px solid var(--warning)', background: 'rgba(255,193,7,0.05)', animation: 'pulse 3s infinite' }}>
                <h3 style={{ color: 'var(--warning)', display: 'flex', gap: '10px', marginBottom: '16px' }}><AlertTriangle size={20} /> Recovery Needed</h3>
                {healthIssues.map((issue, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <span><b style={{ color: 'var(--warning)' }}>[{issue.domain}]</b> {issue.msg}</span>
                    <button className="nav-item badge-warning" style={{ fontSize: '11px', padding: '4px 12px' }}>FIX: {issue.fix}</button>
                  </div>
                ))}
              </section>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
              <div className="glass-card metrics-card">
                <Cpu size={24} color="var(--primary)" />
                <span style={{ fontSize: '26px', fontWeight: 700 }}>{systemStatus?.metrics?.cpu ?? 0}%</span>
                <p style={{ color: 'var(--text-dim)', fontSize: '12px', display: 'flex', justifyContent: 'space-between' }}>CPU Usage <Sparkline data={(systemStatus?.history || []).map((h: any) => h.cpu)} color="var(--primary)" width={60} height={20} /></p>
              </div>
              <div className="glass-card metrics-card">
                <Monitor size={24} color="var(--success)" />
                <span style={{ fontSize: '26px', fontWeight: 700 }}>
                  {((systemStatus?.metrics?.ram_used ?? 0) / 1024 / 1024 / 1024).toFixed(1)} GB
                </span>
                <p style={{ color: 'var(--text-dim)', fontSize: '12px' }}>
                  / {((systemStatus?.metrics?.ram_total ?? 0) / 1024 / 1024 / 1024).toFixed(1)} GB RAM
                </p>
              </div>
              <div className="glass-card metrics-card">
                <HardDrive size={24} color="#a855f7" />
                <span style={{ fontSize: '26px', fontWeight: 700 }}>
                  {((systemStatus?.metrics?.disk_used ?? 0) / 1024 / 1024 / 1024).toFixed(0)} GB
                </span>
                <p style={{ color: 'var(--text-dim)', fontSize: '12px' }}>
                  / {((systemStatus?.metrics?.disk_total ?? 0) / 1024 / 1024 / 1024).toFixed(0)} GB Used
                </p>
              </div>
              <div className="glass-card metrics-card" style={{ position: 'relative' }}>
                <Globe size={24} color="#3b82f6" />
                <span style={{ fontSize: '26px', fontWeight: 700 }}>{systemStatus?.pulse === 'green' ? 'Stable' : 'Unstable'}</span>
                <p style={{ color: 'var(--text-dim)', fontSize: '12px' }}>Fleet Health</p>
              </div>
            </div>

            <section className="glass-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h3 style={{ margin: 0 }}>Active Inventory</h3>
                <span className="badge-dim badge" style={{ fontSize: '10px' }}>{(systemStatus?.servers || []).length} Registered</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
                {(systemStatus?.servers || []).map((s: any) => (
                  <div key={s.id} className="glass-card metrics-card" style={{ padding: '20px', borderLeft: `4px solid ${s.status === 'online' ? '#10b981' : '#ef4444'}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <b style={{ fontSize: '16px' }}>{s.name}</b>
                        <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '4px' }}>TYPE: {(s.type || 'server').toUpperCase()}</div>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                        <span className={`badge ${s.status === 'online' ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: '10px' }}>{s.status}</span>
                        {s.metrics?.pid && (
                          <div style={{ display: 'flex', gap: '4px' }}>
                            <span className="badge badge-dim" style={{ fontSize: '9px' }}>PID: {s.metrics.pid}</span>
                            <span className="badge badge-dim" style={{ fontSize: '9px' }}>CPU: {s.metrics.cpu?.toFixed(1) ?? 0}%</span>
                            <span className="badge badge-dim" style={{ fontSize: '9px' }}>RAM: {(s.metrics.ram / 1024 / 1024).toFixed(0)}MB</span>
                          </div>
                        )}
                      </div>
                    </div>
                    <div style={{ marginTop: '20px', display: 'flex', gap: '8px' }}>
                      <button className={`nav-item ${s.status === 'online' ? 'badge-danger' : 'badge-success'}`} style={{ flex: 1, justifyContent: 'center', fontSize: '12px' }} onClick={() => handleControl(s.id, s.status === 'online' ? 'stop' : 'start')}>
                        {s.status === 'online' ? 'Stop' : 'Start'}
                      </button>
                      <button className="nav-item" style={{ padding: '8px' }} onClick={() => setSelectedItem(s.raw)} title="Inspect Server State">
                        <Search size={18} />
                      </button>
                      {!['mcp-injector', 'mcp-server-manager', 'repo-mcp-packager', 'nexus-librarian'].includes(s.id) ? (
                        <button className="nav-item" style={{ padding: '8px', color: 'var(--danger)' }} onClick={async () => {
                          if (confirm(`CAUTION: Are you sure you want to remove '${s.name}' from the inventory? This will not uninstall the code, but the GUI will no longer manage it.`)) {
                            const res = await fetch('http://127.0.0.1:5001/server/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: s.id }) });
                            if (res.ok) {
                              addNotification(`Removed ${s.name} from inventory.`, 'success');
                              fetchData();
                            } else {
                              const data = await res.json();
                              addNotification(data.error || 'Failed to remove server.', 'error');
                            }
                          }
                        }} title="Remove from Inventory">
                          <Trash2 size={18} />
                        </button>
                      ) : (
                        <button className="nav-item" style={{ padding: '8px', opacity: 0.3, cursor: 'not-allowed' }} title="Core component - Removal via Lifecycle only">
                          <ShieldCheck size={18} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
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
                        <button className="nav-item" style={{ border: 'none', color: '#ef4444', background: 'transparent' }} onClick={() => {
                          if (confirm(`Are you sure you want to delete "${l.title}" from the knowledge base?`)) {
                            fetch('http://127.0.0.1:5001/librarian/resource/delete', {
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
                window.open('http://127.0.0.1:5001/export/report', '_blank');
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
                    <span style={{ flex: 1, fontWeight: log.level === 'ERROR' ? 700 : 500, color: log.level === 'ERROR' ? '#ef4444' : log.level === 'COMMAND' ? '#3b82f6' : 'inherit' }}>{log.message}</span>
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
                <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <ShieldCheck size={20} color="var(--primary)" />
                  {tool.name}
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginBottom: '20px' }}>{tool.description}</p>
                {tool.actions.map((act: any, idx: number) => (
                  <div key={idx} className="glass-card" style={{ padding: '16px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', marginBottom: '16px', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ flex: 1 }}><b>{act.name}</b><br /><small style={{ opacity: 0.6, fontSize: '11px' }}>{act.desc}</small></div>
                      <button className="nav-item badge-success" style={{ padding: '4px 12px' }} onClick={() => {
                        const v = catalogInputs[`${tool.id}-${idx}`] || '';
                        handleRun(`${tool.bin} ${act.cmd} ${v}`.trim());
                      }}>RUN</button>
                    </div>
                    {act.arg && (
                      <div style={{ marginTop: '12px' }}>
                        <input
                          className="glass-card" style={{ width: '100%', padding: '8px 12px', fontSize: '12px', background: 'rgba(0,0,0,0.2)' }}
                          placeholder={`Required: ${act.arg}`}
                          onChange={e => setCatalogInputs({ ...catalogInputs, [`${tool.id}-${idx}`]: e.target.value })}
                        />
                      </div>
                    )}
                  </div>
                ))}
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

        {activeTab === 'lifecycle' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', animation: 'slideIn 0.3s ease-out' }}>
            <section className="glass-card">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}><Search size={20} color="var(--primary)" /> Scan Integration</h3>
              <p style={{ color: 'var(--text-dim)', fontSize: '13px', margin: '8px 0 20px' }}>Registered scan roots are indexed by the Nexus Librarian.</p>
              <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
                <input className="glass-card" style={{ flex: 1, padding: '12px 16px', background: 'rgba(0,0,0,0.3)' }} id="root-entry" placeholder="Absolute local path" />
                <button className="nav-item badge-success" style={{ padding: '0 24px' }} onClick={async () => {
                  const p = (document.getElementById('root-entry') as HTMLInputElement).value;
                  if (!p) return addNotification("Path cannot be empty.", "error");
                  const res = await fetch('http://127.0.0.1:5001/librarian/roots', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: p }) });
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
                        fetch(`http://127.0.0.1:5001/librarian/roots?id=${r.id}`, { method: 'DELETE' }).then(() => {
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
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}><HardDrive size={20} color="#a855f7" /> State Snapshots</h3>
              <p style={{ color: 'var(--text-dim)', fontSize: '13px', margin: '8px 0 20px' }}>Rollback to restore known good configurations.</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {inventoryHistory.map((h, i) => (
                  <div key={i} className="table-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px' }}>
                    <div>
                      <b style={{ fontSize: '14px' }}>{h.name}</b>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>Captured: {new Date(h.time * 1000).toLocaleString()}</div>
                    </div>
                    <button className="nav-item" style={{ border: '1px solid rgba(168, 85, 247, 0.4)', color: '#a855f7' }} onClick={() => {
                      if (confirm("DANGER: Rollback will overwrite current configuration. Proceed?")) {
                        fetch('http://127.0.0.1:5001/project/rollback', {
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

            <div className="glass-card" style={{ border: '1px solid #ef4444', background: 'rgba(239, 68, 68, 0.05)', padding: '24px' }}>
              <h3 style={{ color: '#ef4444', marginBottom: '8px' }}>Critical Maintenance</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-dim)', marginBottom: '24px' }}>FACTORY RESET: This action will permanently remove all Nexus binaries and data.</p>
              <button className="nav-item" style={{ borderColor: '#ef4444', color: '#ef4444', width: '100%', padding: '14px', fontWeight: 700 }} onClick={() => {
                if (confirm("UNINSTALL everything?")) {
                  addNotification("Uninstall sequence started...", "error");
                  fetch('http://127.0.0.1:5001/system/uninstall', { method: 'POST' }).then(res => {
                    if (res.ok) window.location.reload();
                  });
                }
              }}>PURGE ENTIRE SUITE</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
