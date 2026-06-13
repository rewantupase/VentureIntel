import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getStatus } from '../utils/api';
import {
  Search, Users, BarChart2, AlertTriangle,
  CheckSquare, FileText, ArrowRight, Zap
} from 'lucide-react';

const AGENTS = [
  { key: 'research_agent', label: 'Research Agent', icon: Search, color: 'var(--accent)' },
  { key: 'competitor_discovery_agent', label: 'Competitor Discovery', icon: Users, color: 'var(--accent2)' },
  { key: 'competitor_analysis_agent', label: 'Competitor Analysis', icon: BarChart2, color: 'var(--accent2)' },
  { key: 'risk_analysis_agent', label: 'Risk Analysis', icon: AlertTriangle, color: 'var(--warn)' },
  { key: 'verification_agent', label: 'Verification', icon: CheckSquare, color: 'var(--accent3)' },
  { key: 'report_agent', label: 'Report Generation', icon: FileText, color: 'var(--success)' },
];

const STATUS_ORDER = [
  'queued', 'collecting_evidence', 'running_agents',
  'verifying', 'generating_report', 'completed', 'failed',
];

function ProgressBar({ value }) {
  return (
    <div style={{ height: 4, background: 'var(--bg3)', borderRadius: 2, overflow: 'hidden' }}>
      <div style={{
        height: '100%', width: `${value}%`,
        background: 'linear-gradient(90deg, var(--accent), var(--accent2))',
        transition: 'width 0.5s ease', borderRadius: 2,
      }} />
    </div>
  );
}

export default function SessionPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await getStatus(sessionId);
        setStatus(data);
        if (data.status === 'completed') {
          setTimeout(() => navigate(`/report/${sessionId}`), 1500);
        }
      } catch (e) {}
    };
    poll();
    const interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, [sessionId, navigate]);

  useEffect(() => {
    const t = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const completedAgents = status?.agents?.map(a => a.name) || [];
  const statusIdx = STATUS_ORDER.indexOf(status?.status || 'queued');
  const overallProgress = Math.min(Math.round((statusIdx / (STATUS_ORDER.length - 1)) * 100), 100);

  const agentStatus = (key) => {
    if (completedAgents.includes(key)) return 'done';
    const currentIdx = STATUS_ORDER.indexOf(status?.status || 'queued');
    const agentIdx = AGENTS.findIndex(a => a.key === key);
    if (currentIdx >= 2 && agentIdx <= 3) return 'running';
    if (currentIdx >= 4 && agentIdx === 4) return 'running';
    if (currentIdx >= 5 && agentIdx === 5) return 'running';
    return 'pending';
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      {/* Header */}
      <header style={{
        borderBottom: '1px solid var(--border)', padding: '16px 32px',
        display: 'flex', alignItems: 'center', gap: 10, background: 'var(--bg2)',
      }}>
        <Zap size={20} color="var(--accent)" />
        <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, color: 'var(--accent)' }}>INTEL.AI</span>
        <ArrowRight size={14} color="var(--text3)" />
        <span style={{ color: 'var(--text2)' }}>{status?.company || 'Loading...'}</span>
      </header>

      <div style={{ maxWidth: 800, margin: '0 auto', padding: '48px 32px' }}>
        {/* Status banner */}
        <div className="card" style={{ marginBottom: 32, position: 'relative', overflow: 'hidden' }}>
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0,
            height: 2,
            background: status?.status === 'completed'
              ? 'var(--success)'
              : 'linear-gradient(90deg, var(--accent), var(--accent2))',
            animation: status?.status !== 'completed' ? 'pulse-glow 2s infinite' : 'none',
          }} />
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div>
              <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 4 }}>
                {status?.company ? `Analyzing ${status.company}` : 'Starting research...'}
              </h2>
              <p style={{ color: 'var(--text2)', fontSize: 13 }}>
                {status?.status?.replace(/_/g, ' ').toUpperCase() || 'QUEUED'}
                {' · '}{Math.floor(elapsed / 60)}m {elapsed % 60}s elapsed
              </p>
            </div>
            <span className={`badge badge-${status?.status || 'queued'}`} style={{ fontSize: 13, padding: '4px 14px' }}>
              {status?.status || 'queued'}
            </span>
          </div>
          <ProgressBar value={overallProgress} />
          <p style={{ color: 'var(--text3)', fontSize: 12, marginTop: 6, textAlign: 'right' }}>
            {overallProgress}%
          </p>
        </div>

        {/* Agent cards */}
        <p style={{ color: 'var(--text3)', fontSize: 12, fontFamily: 'var(--mono)', marginBottom: 16, letterSpacing: '0.08em' }}>
          AGENT PIPELINE
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 40 }}>
          {AGENTS.map((agent, i) => {
            const aStatus = agentStatus(agent.key);
            const Icon = agent.icon;
            return (
              <div key={agent.key} className="card" style={{
                display: 'flex', alignItems: 'center', gap: 16,
                opacity: aStatus === 'pending' ? 0.5 : 1,
                transition: 'opacity 0.3s',
                borderColor: aStatus === 'running' ? agent.color : 'var(--border)',
              }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10,
                  background: `${agent.color}22`,
                  border: `1px solid ${agent.color}44`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <Icon size={18} color={agent.color} />
                </div>
                <div style={{ flex: 1 }}>
                  <p style={{ fontWeight: 500, marginBottom: 2 }}>{agent.label}</p>
                  <p style={{ color: 'var(--text3)', fontSize: 12 }}>
                    {aStatus === 'done' && 'Completed'}
                    {aStatus === 'running' && 'Running with Phi-3...'}
                    {aStatus === 'pending' && 'Waiting...'}
                  </p>
                </div>
                <div>
                  {aStatus === 'done' && (
                    <div style={{ width: 20, height: 20, borderRadius: '50%', background: 'var(--success)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <span style={{ color: 'white', fontSize: 12 }}>✓</span>
                    </div>
                  )}
                  {aStatus === 'running' && <div className="spinner" />}
                  {aStatus === 'pending' && (
                    <div style={{ width: 20, height: 20, borderRadius: '50%', border: '2px solid var(--border)' }} />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {status?.status === 'completed' && (
          <div style={{ textAlign: 'center' }}>
            <p style={{ color: 'var(--success)', marginBottom: 12 }}>✓ Analysis complete! Redirecting to report...</p>
          </div>
        )}

        {status?.status === 'failed' && (
          <div className="card" style={{ borderColor: 'var(--danger)', textAlign: 'center' }}>
            <p style={{ color: 'var(--danger)' }}>Research failed. Please try again.</p>
            <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={() => navigate('/')}>
              Back to Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
