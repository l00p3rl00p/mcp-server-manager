import React, { useState, useEffect } from 'react';
import {
  Activity,
  Database,
  Terminal,
  ShieldCheck,
  Settings,
  LayoutDashboard,
  Search,
  RefreshCw,
} from 'lucide-react';

// Types
interface LogEntry {
  timestamp: number;
  iso: string;
  level: string;
  message: string;
  suggestion?: string;
}

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [systemStatus, setSystemStatus] = useState<any>({});
  const [artifacts, setArtifacts] = useState<any[]>([]);

  // Real-time Data Fetching
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [logsRes, statusRes, artifactsRes] = await Promise.all([
          fetch('http://127.0.0.1:5001/logs'),
          fetch('http://127.0.0.1:5001/status'),
          fetch('http://127.0.0.1:5001/artifacts')
        ]);

        if (logsRes.ok) setLogs(await logsRes.json());
        if (statusRes.ok) setSystemStatus(await statusRes.json());
        if (artifactsRes.ok) setArtifacts(await artifactsRes.json());
      } catch (err) {
        console.error("Bridge connection failed:", err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleControl = async (id: string, action: string) => {
    try {
      await fetch('http://127.0.0.1:5001/server/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, action })
      });
    } catch (err) {
      console.error("Control failed:", err);
    }
  };

  return (
    <div className="app-container">
      <div className="liquid-bg"></div>

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={32} />
          <span>Nexus</span>
        </div>

        <div className="nav-group">
          <p style={{ fontSize: '10px', color: 'var(--text-dim)', marginLeft: '16px', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '1px' }}>Workspaces</p>
          <div className="nav-item active">
            <ShieldCheck size={18} /> Global Session
          </div>
          <div className="nav-item">
            <RefreshCw size={18} /> New Session...
          </div>
        </div>

        <nav className="nav-group">
          <p style={{ fontSize: '10px', color: 'var(--text-dim)', marginLeft: '16px', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '1px' }}>Modules</p>
          <div
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <LayoutDashboard size={20} /> Dashboard
          </div>
          <div
            className={`nav-item ${activeTab === 'librarian' ? 'active' : ''}`}
            onClick={() => setActiveTab('librarian')}
          >
            <Database size={20} /> Librarian
          </div>
          <div
            className={`nav-item ${activeTab === 'terminal' ? 'active' : ''}`}
            onClick={() => setActiveTab('terminal')}
          >
            <Terminal size={20} /> Command Log
          </div>
        </nav>

        <div style={{ marginTop: 'auto' }} className="nav-group">
          <div className="nav-item">
            <Settings size={20} /> Settings
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-viewport">
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '32px', marginBottom: '4px' }}>Workforce Nexus</h1>
            <p style={{ color: 'var(--text-dim)' }}>System Observability & Mission Control</p>
          </div>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div className="glass-card" style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div className="thinking-indicator"></div>
              <span style={{ fontSize: '14px', fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>
                {systemStatus.posture || 'Initializing...'}
              </span>
            </div>
            <div className="glass-card" style={{ padding: '8px 16px' }}>
              <span className="badge badge-success">Online</span>
            </div>
          </div>
        </header>

        {/* Tabbed Content Areas */}
        {activeTab === 'dashboard' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px' }}>

            {/* Server Management Grid */}
            <section className="glass-card" style={{ gridColumn: 'span 2' }}>
              <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
                <Activity size={24} color="var(--primary)" /> Managed MCP Servers
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
                {(systemStatus.servers && systemStatus.servers.length > 0) ? (
                  systemStatus.servers.map((server: any) => (
                    <div key={server.id} className="glass-card" style={{ padding: '16px', background: 'rgba(210, 230, 255, 0.03)', position: 'relative' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <span style={{ fontWeight: 600, fontSize: '16px' }}>{server.name}</span>
                        <span className={`badge ${server.status === 'online' ? 'badge-success' : 'badge-warning'}`}>
                          {server.status}
                        </span>
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginBottom: '16px' }}>Type: {server.type}</p>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button className="nav-item" style={{ padding: '4px 12px', fontSize: '12px', flex: 1 }} onClick={() => handleControl(server.id, 'start')}>Start</button>
                        <button className="nav-item" style={{ padding: '4px 12px', fontSize: '12px', flex: 1, border: '1px solid var(--danger)', color: 'var(--danger)' }} onClick={() => handleControl(server.id, 'stop')}>Stop</button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="glass-card" style={{ gridColumn: 'span 3', textAlign: 'center', padding: '40px', color: 'var(--text-dim)' }}>
                    No servers detected in active inventory.
                  </div>
                )}
              </div>
            </section>

            {/* Thinking / Posture */}
            <section className="glass-card">
              <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
                <Search size={24} color="var(--primary)" /> Internal Posture
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {logs.filter(l => l.level === 'THINKING').map((log, i) => (
                  <div key={i} style={{ borderLeft: '2px solid var(--primary)', paddingLeft: '16px' }}>
                    <p style={{ fontWeight: 600 }}>{log.message}</p>
                    <p style={{ fontSize: '14px', color: 'var(--text-dim)', marginTop: '4px' }}>{log.suggestion}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* Recent Commands Snippet */}
            <section className="glass-card">
              <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
                <Terminal size={24} color="var(--primary)" /> Recent Commands
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {logs.slice(0, 5).map((log, i) => (
                  <div key={i} style={{ fontSize: '13px', paddingBottom: '8px', borderBottom: '1px solid var(--card-border)' }}>
                    <span style={{ color: 'var(--primary)', fontVariantNumeric: 'tabular-nums' }}>{log.iso.split('T')[1].slice(0, 8)}</span> {log.message}
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}

        {/* Librarian Tab (Artifacts) */}
        {activeTab === 'librarian' && (
          <div className="glass-card">
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
              <Database size={24} color="var(--primary)" /> Artifact Explorer
            </h2>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--card-border)', color: 'var(--text-dim)', fontSize: '14px' }}>
                    <th style={{ padding: '12px' }}>Name</th>
                    <th style={{ padding: '12px' }}>Disk Path</th>
                    <th style={{ padding: '12px' }}>Size</th>
                    <th style={{ padding: '12px' }}>Modified</th>
                  </tr>
                </thead>
                <tbody>
                  {artifacts.length > 0 ? artifacts.map((art, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '12px', fontWeight: 500 }}>{art.name}</td>
                      <td style={{ padding: '12px', fontSize: '12px', color: 'var(--text-dim)' }}>{art.path}</td>
                      <td style={{ padding: '12px', color: 'var(--text-dim)' }}>{(art.size / 1024).toFixed(1)} KB</td>
                      <td style={{ padding: '12px', color: 'var(--text-dim)', fontSize: '12px' }}>{new Date(art.modified * 1000).toLocaleString()}</td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan={4} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-dim)' }}>No artifacts indexed.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Master Command Log Tab */}
        {activeTab === 'terminal' && (
          <section className="glass-card">
            <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
              <Terminal size={24} color="var(--primary)" /> Master Command Log
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '70vh', overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                <thead>
                  <tr style={{ color: 'var(--text-dim)', borderBottom: '1px solid var(--card-border)' }}>
                    <th style={{ textAlign: 'left', padding: '12px', width: '160px' }}>Timestamp</th>
                    <th style={{ textAlign: 'left', padding: '12px', width: '100px' }}>Level</th>
                    <th style={{ textAlign: 'left', padding: '12px' }}>Message</th>
                    <th style={{ textAlign: 'left', padding: '12px', width: '30%' }}>Suggestion / Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.slice().reverse().map((log, i) => ( // Reverse to show latest first
                    <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                      <td style={{ padding: '12px', color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums', verticalAlign: 'top' }}>
                        {new Date(log.timestamp * 1000).toLocaleString(undefined, {
                          hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
                        })}
                      </td>
                      <td style={{ padding: '12px', verticalAlign: 'top' }}>
                        <span className={`badge ${log.level === 'ERROR' ? 'badge-danger' :
                          (log.level === 'THINKING' ? 'badge-warning' : 'badge-success')
                          }`}>
                          {log.level}
                        </span>
                      </td>
                      <td style={{ padding: '12px', fontWeight: 500, verticalAlign: 'top', fontFamily: 'monospace' }}>
                        {log.message}
                      </td>
                      <td style={{ padding: '12px', color: 'var(--text-dim)', fontSize: '13px', verticalAlign: 'top' }}>
                        {log.suggestion || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
};

export default App;
