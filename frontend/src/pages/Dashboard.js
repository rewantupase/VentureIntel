import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Zap, Clock, CheckCircle, AlertTriangle, Cpu, GitBranch, Wrench } from 'lucide-react';
import { startResearch, listSessions, getLLMStatus, getChromaStatus, getMCPTools, getGraphSchema } from '../utils/api';

export default function Dashboard() {
  const [company, setCompany]       = useState('');
  const [loading, setLoading]       = useState(false);
  const [sessions, setSessions]     = useState([]);
  const [llmStatus, setLLMStatus]   = useState(null);
  const [chromaStatus, setChroma]   = useState(null);
  const [mcpTools, setMCPTools]     = useState([]);
  const [graphSchema, setGraph]     = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    listSessions().then(setSessions).catch(() => {});
    getLLMStatus().then(setLLMStatus).catch(() => {});
    getChromaStatus().then(setChroma).catch(() => {});
    getMCPTools().then(d => setMCPTools(d.tools || [])).catch(() => {});
    getGraphSchema().then(setGraph).catch(() => {});
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!company.trim()) return;
    setLoading(true);
    try {
      const res = await startResearch(company.trim());
      navigate(`/session/${res.session_id}`);
    } catch {
      alert('Failed to start research. Is the backend running?');
    } finally { setLoading(false); }
  };

  const statusDot = (ok) => (
    <div style={{ width:8, height:8, borderRadius:'50%',
      background: ok ? 'var(--success)' : 'var(--danger)', flexShrink:0 }} />
  );

  return (
    <div style={{ minHeight:'100vh', display:'flex', flexDirection:'column' }}>
      {/* Header */}
      <header style={{ borderBottom:'1px solid var(--border)', padding:'14px 32px',
        display:'flex', alignItems:'center', justifyContent:'space-between',
        background:'var(--bg2)' }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <Zap size={20} color="var(--accent)" />
          <span style={{ fontFamily:'var(--mono)', fontWeight:700, fontSize:15, color:'var(--accent)' }}>
            INTEL<span style={{ color:'var(--text2)' }}>.AI</span>
          </span>
          <span style={{ fontSize:11, padding:'2px 8px', borderRadius:10,
            background:'rgba(139,92,246,0.15)', color:'var(--accent3)',
            border:'1px solid rgba(139,92,246,0.3)', fontFamily:'var(--mono)' }}>
            v2 · LangGraph
          </span>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:14 }}>
          {[
            { label:`Phi-3 · ${llmStatus?.available ? 'ON':'OFF'}`, ok: llmStatus?.available },
            { label:`ChromaDB · ${chromaStatus?.status==='ok' ? 'OK':'ERR'}`, ok: chromaStatus?.status==='ok' },
            { label:`${mcpTools.length} MCP tools`, ok: mcpTools.length > 0 },
          ].map(({ label, ok }) => (
            <div key={label} style={{ display:'flex', alignItems:'center', gap:6 }}>
              {statusDot(ok)}
              <span style={{ fontSize:11, color:'var(--text2)', fontFamily:'var(--mono)' }}>{label}</span>
            </div>
          ))}
        </div>
      </header>

      <div style={{ flex:1, maxWidth:1000, margin:'0 auto', padding:'48px 32px', width:'100%' }}>
        {/* Hero */}
        <div style={{ textAlign:'center', marginBottom:40 }}>
          <div style={{ display:'inline-block', background:'rgba(59,130,246,0.1)',
            border:'1px solid rgba(59,130,246,0.2)', borderRadius:20, padding:'4px 14px',
            fontSize:11, fontFamily:'var(--mono)', color:'var(--accent)', marginBottom:16,
            letterSpacing:'0.1em' }}>
            LANGGRAPH PIPELINE · CHROMADB · LOCAL PHI-3 · MCP TOOLS · NO DATA LEAVES YOUR MACHINE
          </div>
          <h1 style={{ fontSize:'clamp(26px,5vw,44px)', fontWeight:700, lineHeight:1.15, marginBottom:12 }}>
            Competitive Intelligence<br/>
            <span style={{ color:'var(--accent)' }}>Powered by Local AI</span>
          </h1>
          <p style={{ color:'var(--text2)', fontSize:15, maxWidth:520, margin:'0 auto' }}>
            Multi-agent system with LangGraph orchestration, MCP data tools, 
            deterministic cross-source verification, and local Phi-3 for analysis.
          </p>
        </div>

        {/* Search */}
        <form onSubmit={handleSubmit} style={{ marginBottom:36 }}>
          <div style={{ display:'flex', gap:12, background:'var(--bg2)',
            border:'1px solid var(--border)', borderRadius:12, padding:8,
            boxShadow:'var(--glow)' }}>
            <div style={{ flex:1, display:'flex', alignItems:'center', gap:10, padding:'0 8px' }}>
              <Search size={18} color="var(--text3)" />
              <input value={company} onChange={e => setCompany(e.target.value)}
                placeholder="Enter company name (e.g. OpenAI, Notion, Stripe...)"
                style={{ border:'none', background:'transparent', fontSize:16,
                  padding:'8px 0', width:'100%' }} />
            </div>
            <button type="submit" className="btn btn-primary"
              disabled={loading || !company.trim()}
              style={{ padding:'10px 28px', fontSize:15 }}>
              {loading ? <><div className="spinner"/> Launching...</> : <><Zap size={16}/> Analyze</>}
            </button>
          </div>
        </form>

        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:20, marginBottom:36 }}>
          {/* LangGraph pipeline */}
          <div className="card">
            <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:14 }}>
              <GitBranch size={15} color="var(--accent)" />
              <p style={{ color:'var(--text3)', fontSize:11, fontFamily:'var(--mono)',
                letterSpacing:'0.08em' }}>LANGGRAPH PIPELINE</p>
            </div>
            {graphSchema ? (
              <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
                {graphSchema.nodes.map((node, i) => (
                  <div key={node} style={{ display:'flex', alignItems:'center', gap:8 }}>
                    <div style={{ width:24, height:24, borderRadius:6,
                      background: i===1 ? 'rgba(6,182,212,0.15)' : 'rgba(59,130,246,0.1)',
                      border: `1px solid ${i===1 ? 'rgba(6,182,212,0.3)' : 'rgba(59,130,246,0.2)'}`,
                      display:'flex', alignItems:'center', justifyContent:'center',
                      fontSize:10, color:'var(--accent2)', fontWeight:700 }}>{i+1}</div>
                    <span style={{ fontSize:12, color:'var(--text2)',
                      fontFamily:'var(--mono)' }}>{node}</span>
                    {node === 'parallel_agents' && (
                      <span style={{ fontSize:10, color:'var(--accent2)',
                        background:'rgba(6,182,212,0.1)', padding:'1px 6px', borderRadius:4 }}>
                        ×3 parallel
                      </span>
                    )}
                    {node === 'verification' && (
                      <span style={{ fontSize:10, color:'var(--success)',
                        background:'rgba(16,185,129,0.1)', padding:'1px 6px', borderRadius:4 }}>
                        no LLM
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="spinner" />
            )}
          </div>

          {/* MCP Tools */}
          <div className="card">
            <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:14 }}>
              <Wrench size={15} color="var(--accent3)" />
              <p style={{ color:'var(--text3)', fontSize:11, fontFamily:'var(--mono)',
                letterSpacing:'0.08em' }}>MCP DATA TOOLS</p>
            </div>
            {mcpTools.length > 0 ? (
              <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
                {mcpTools.map(tool => (
                  <div key={tool.name} style={{ display:'flex', alignItems:'center',
                    justifyContent:'space-between' }}>
                    <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                      <div style={{ width:6, height:6, borderRadius:'50%',
                        background:'var(--accent3)' }} />
                      <span style={{ fontSize:12, color:'var(--text2)',
                        fontFamily:'var(--mono)' }}>{tool.name}</span>
                    </div>
                    <span style={{ fontSize:10, color:'var(--text3)',
                      background:'var(--bg3)', padding:'1px 6px', borderRadius:4,
                      border:'1px solid var(--border)' }}>
                      cred:{tool.credibility}
                    </span>
                  </div>
                ))}
              </div>
            ) : <div className="spinner" />}
          </div>
        </div>

        {/* Recent sessions */}
        {sessions.length > 0 && (
          <div>
            <p style={{ color:'var(--text3)', fontSize:11, fontFamily:'var(--mono)',
              marginBottom:12, letterSpacing:'0.08em' }}>RECENT RESEARCH</p>
            <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
              {sessions.slice(0,8).map(s => (
                <div key={s.session_id}
                  onClick={() => navigate(s.status==='completed'
                    ? `/report/${s.session_id}` : `/session/${s.session_id}`)}
                  style={{ display:'flex', alignItems:'center', justifyContent:'space-between',
                    background:'var(--bg2)', border:'1px solid var(--border)',
                    borderRadius:8, padding:'12px 16px', cursor:'pointer', transition:'border-color 0.15s' }}
                  onMouseEnter={e => e.currentTarget.style.borderColor='var(--accent)'}
                  onMouseLeave={e => e.currentTarget.style.borderColor='var(--border)'}>
                  <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                    {s.status==='completed'
                      ? <CheckCircle size={14} color="var(--success)"/>
                      : s.status==='failed'
                      ? <AlertTriangle size={14} color="var(--danger)"/>
                      : <div className="spinner"/>}
                    <span style={{ fontWeight:500 }}>{s.company}</span>
                  </div>
                  <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                    <span className={`badge badge-${s.status}`}>{s.status}</span>
                    <span style={{ color:'var(--text3)', fontSize:12, display:'flex',
                      alignItems:'center', gap:4 }}>
                      <Clock size={12}/> {new Date(s.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
