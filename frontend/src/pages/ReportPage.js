import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts';
import {
  Download, MessageSquare, Send, ArrowLeft,
  Shield, Users, TrendingUp, FileText, CheckCircle, Zap,
} from 'lucide-react';
import { getReport, sendChat, getPDFUrl } from '../utils/api';

const SEV_COLOR = { high: '#ef4444', medium: '#f59e0b', low: '#10b981' };

function RiskRadar({ risks }) {
  const data = risks.map(r => ({
    category: r.category.replace(/_/g, ' ').split(' ').map(w => w[0].toUpperCase() + w.slice(1)).join(' '),
    score: r.score,
  }));
  return (
    <ResponsiveContainer width="100%" height={250}>
      <RadarChart data={data}>
        <PolarGrid stroke="var(--border)" />
        <PolarAngleAxis dataKey="category" tick={{ fill: 'var(--text2)', fontSize: 11 }} />
        <Radar dataKey="score" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.2} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

function CompetitorBar({ competitors }) {
  const data = Object.entries(competitors).map(([name, c]) => ({
    name,
    strengths: (c.strengths || []).length,
    weaknesses: (c.weaknesses || []).length,
  }));
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ left: -20 }}>
        <XAxis dataKey="name" tick={{ fill: 'var(--text2)', fontSize: 11 }} />
        <YAxis tick={{ fill: 'var(--text2)', fontSize: 11 }} />
        <Tooltip contentStyle={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 8 }} />
        <Bar dataKey="strengths" fill="var(--accent)" radius={[4, 4, 0, 0]} name="Strengths" />
        <Bar dataKey="weaknesses" fill="var(--danger)" radius={[4, 4, 0, 0]} name="Weaknesses" />
      </BarChart>
    </ResponsiveContainer>
  );
}

function ChatPanel({ sessionId }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'Ask me anything about this research. I\'ll answer based on the verified evidence.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef();

  const send = async () => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput('');
    setMessages(m => [...m, { role: 'user', text: question }]);
    setLoading(true);
    try {
      const res = await sendChat(sessionId, question);
      setMessages(m => [...m, { role: 'assistant', text: res.response, sources: res.sources }]);
    } catch {
      setMessages(m => [...m, { role: 'assistant', text: 'Error: Could not reach the AI. Is the backend running?' }]);
    } finally {
      setLoading(false);
    }
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 500 }}>
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0' }}>
        {messages.map((m, i) => (
          <div key={i} style={{
            alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
            maxWidth: '85%',
          }}>
            <div style={{
              background: m.role === 'user' ? 'var(--accent)' : 'var(--bg3)',
              border: m.role === 'user' ? 'none' : '1px solid var(--border)',
              borderRadius: 10, padding: '10px 14px',
              fontSize: 13, lineHeight: 1.6,
            }}>
              {m.text}
            </div>
            {m.sources?.length > 0 && (
              <p style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4, paddingLeft: 4 }}>
                Sources: {m.sources.slice(0, 2).map((s, i) => (
                  <a key={i} href={s} target="_blank" rel="noopener noreferrer"
                    style={{ color: 'var(--accent)', marginRight: 6 }}>[{i+1}]</a>
                ))}
              </p>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ alignSelf: 'flex-start' }}>
            <div style={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 10, padding: '10px 14px' }}>
              <div className="spinner" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div style={{ display: 'flex', gap: 8, paddingTop: 12, borderTop: '1px solid var(--border)', marginTop: 12 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="Ask about funding, competitors, risks..."
        />
        <button className="btn btn-primary" onClick={send} disabled={loading} style={{ padding: '10px 16px', flexShrink: 0 }}>
          <Send size={15} />
        </button>
      </div>
    </div>
  );
}

export default function ReportPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getReport(sessionId)
      .then(setReport)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center' }}>
        <div className="spinner" style={{ width: 32, height: 32, margin: '0 auto 16px' }} />
        <p style={{ color: 'var(--text2)' }}>Loading report...</p>
      </div>
    </div>
  );

  if (!report) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ textAlign: 'center' }}>
        <p style={{ color: 'var(--danger)', marginBottom: 12 }}>Report not found or not yet ready.</p>
        <button className="btn btn-secondary" onClick={() => navigate('/')}>Go Back</button>
      </div>
    </div>
  );

  const researchData = report.agents?.research_agent || {};
  const discoverData = report.agents?.competitor_discovery_agent || {};
  const analysisData = report.agents?.competitor_analysis_agent?.competitor_analyses || {};
  const riskData = report.agents?.risk_analysis_agent || {};
  const verifyData = report.agents?.verification_agent || {};
  const reportData = report.report || {};
  const risks = report.risk_scores || [];
  const competitors = discoverData.top_competitors || [];
  const verifiedFindings = verifyData.verified_findings || [];
  const avgConf = verifyData.avg_confidence || 0;

  const TABS = [
    { key: 'overview', label: 'Overview', icon: TrendingUp },
    { key: 'competitors', label: 'Competitors', icon: Users },
    { key: 'risks', label: 'Risk Assessment', icon: Shield },
    { key: 'verification', label: 'Verified Findings', icon: CheckCircle },
    { key: 'chat', label: 'AI Chat', icon: MessageSquare },
  ];

  return (
    <div style={{ minHeight: '100vh' }}>
      {/* Header */}
      <header style={{
        borderBottom: '1px solid var(--border)', padding: '14px 32px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'var(--bg2)', position: 'sticky', top: 0, zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-secondary" style={{ padding: '6px 12px' }} onClick={() => navigate('/')}>
            <ArrowLeft size={14} /> Back
          </button>
          <Zap size={18} color="var(--accent)" />
          <span style={{ fontWeight: 600 }}>{report.company_name}</span>
          <span className="badge badge-completed">Report Ready</span>
        </div>
        {report.pdf_available && (
          <a
            href={getPDFUrl(sessionId)}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
            style={{ textDecoration: 'none', padding: '8px 18px' }}
          >
            <Download size={14} /> Download PDF
          </a>
        )}
      </header>

      {/* Tabs */}
      <div style={{
        borderBottom: '1px solid var(--border)', background: 'var(--bg2)',
        display: 'flex', gap: 4, padding: '0 32px', overflowX: 'auto',
      }}>
        {TABS.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                display: 'flex', alignItems: 'center', gap: 7,
                padding: '12px 16px', border: 'none', cursor: 'pointer',
                background: 'transparent', color: activeTab === tab.key ? 'var(--accent)' : 'var(--text2)',
                borderBottom: activeTab === tab.key ? '2px solid var(--accent)' : '2px solid transparent',
                fontSize: 13, fontFamily: 'var(--sans)', fontWeight: 500,
                whiteSpace: 'nowrap', transition: 'color 0.15s',
              }}
            >
              <Icon size={14} />{tab.label}
            </button>
          );
        })}
      </div>

      <div style={{ maxWidth: 1000, margin: '0 auto', padding: '32px' }}>

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {/* Stats row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
              {[
                { label: 'Competitors Found', value: competitors.length, color: 'var(--accent)' },
                { label: 'Risk Score', value: `${riskData.overall_risk_score || 0}/10`, color: 'var(--warn)' },
                { label: 'Claims Verified', value: verifiedFindings.length, color: 'var(--success)' },
                { label: 'Avg Confidence', value: `${Math.round(avgConf * 100)}%`, color: 'var(--accent2)' },
              ].map(stat => (
                <div key={stat.label} className="card" style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: 28, fontWeight: 700, color: stat.color, fontFamily: 'var(--mono)' }}>
                    {stat.value}
                  </p>
                  <p style={{ color: 'var(--text2)', fontSize: 12, marginTop: 4 }}>{stat.label}</p>
                </div>
              ))}
            </div>

            {/* Executive Summary */}
            {reportData.executive_summary && (
              <div className="card">
                <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <FileText size={16} color="var(--accent)" /> Executive Summary
                </h3>
                <p style={{ color: 'var(--text2)', lineHeight: 1.7 }}>{reportData.executive_summary}</p>
                {reportData.key_conclusions?.length > 0 && (
                  <>
                    <h4 style={{ marginTop: 16, marginBottom: 8, fontSize: 13, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>
                      KEY CONCLUSIONS
                    </h4>
                    <ul style={{ paddingLeft: 16, display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {reportData.key_conclusions.map((c, i) => (
                        <li key={i} style={{ color: 'var(--text2)', fontSize: 13 }}>{c}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}

            {/* Company profile */}
            {researchData && (
              <div className="card">
                <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Company Profile</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  {[
                    ['Overview', researchData.overview],
                    ['Founders', researchData.founders],
                    ['Funding', researchData.funding],
                    ['Recent News', researchData.recent_news],
                  ].filter(([, v]) => v).map(([label, value]) => (
                    <div key={label}>
                      <p style={{ color: 'var(--text3)', fontSize: 11, fontFamily: 'var(--mono)', marginBottom: 6, letterSpacing: '0.06em' }}>
                        {label.toUpperCase()}
                      </p>
                      <p style={{ color: 'var(--text2)', fontSize: 13, lineHeight: 1.6 }}>
                        {Array.isArray(value) ? value.join(', ') : value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* COMPETITORS TAB */}
        {activeTab === 'competitors' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {Object.keys(analysisData).length > 0 && (
              <div className="card">
                <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>Strengths vs Weaknesses</h3>
                <CompetitorBar competitors={analysisData} />
              </div>
            )}
            {Object.entries(analysisData).map(([name, c]) => (
              <div key={name} className="card">
                <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>{name}</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 12 }}>
                  <div>
                    <p style={{ color: 'var(--success)', fontSize: 11, fontFamily: 'var(--mono)', marginBottom: 6 }}>STRENGTHS</p>
                    <ul style={{ paddingLeft: 16 }}>
                      {(c.strengths || []).map((s, i) => <li key={i} style={{ color: 'var(--text2)', fontSize: 13, marginBottom: 4 }}>{s}</li>)}
                    </ul>
                  </div>
                  <div>
                    <p style={{ color: 'var(--danger)', fontSize: 11, fontFamily: 'var(--mono)', marginBottom: 6 }}>WEAKNESSES</p>
                    <ul style={{ paddingLeft: 16 }}>
                      {(c.weaknesses || []).map((w, i) => <li key={i} style={{ color: 'var(--text2)', fontSize: 13, marginBottom: 4 }}>{w}</li>)}
                    </ul>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                  {c.market_share_est && <p style={{ fontSize: 12, color: 'var(--text3)' }}>Market Share: <span style={{ color: 'var(--text)' }}>{c.market_share_est}</span></p>}
                  {c.funding_valuation && <p style={{ fontSize: 12, color: 'var(--text3)' }}>Funding: <span style={{ color: 'var(--text)' }}>{c.funding_valuation}</span></p>}
                </div>
              </div>
            ))}
            {Object.keys(analysisData).length === 0 && (
              <div className="card" style={{ textAlign: 'center', color: 'var(--text3)' }}>
                No competitor data available yet.
              </div>
            )}
          </div>
        )}

        {/* RISKS TAB */}
        {activeTab === 'risks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {risks.length > 0 && (
              <div className="card">
                <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>Risk Radar</h3>
                <RiskRadar risks={risks} />
              </div>
            )}
            <div style={{ display: 'grid', gap: 12 }}>
              {Object.entries(riskData).map(([cat, data]) => {
                if (cat === 'overall_risk_score' || cat === 'social_sentiment') return null;
                if (!data?.severity) return null;
                return (
                  <div key={cat} className="card" style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
                    <div style={{
                      width: 4, height: '100%', minHeight: 60,
                      background: SEV_COLOR[data.severity] || 'var(--text3)',
                      borderRadius: 2, flexShrink: 0,
                    }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                        <h4 style={{ fontWeight: 600, fontSize: 14 }}>
                          {cat.replace(/_/g, ' ').split(' ').map(w => w[0].toUpperCase() + w.slice(1)).join(' ')}
                        </h4>
                        <span className={`badge badge-${data.severity}`}>{data.severity}</span>
                      </div>
                      <p style={{ color: 'var(--text2)', fontSize: 13 }}>{data.summary}</p>
                      {data.examples?.length > 0 && (
                        <ul style={{ paddingLeft: 16, marginTop: 8 }}>
                          {data.examples.slice(0, 3).map((ex, i) => (
                            <li key={i} style={{ color: 'var(--text3)', fontSize: 12, marginBottom: 3 }}>{ex}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* VERIFICATION TAB */}
        {activeTab === 'verification' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 8 }}>
              <div className="card" style={{ textAlign: 'center' }}>
                <p style={{ fontSize: 28, fontWeight: 700, color: 'var(--success)', fontFamily: 'var(--mono)' }}>
                  {Math.round(avgConf * 100)}%
                </p>
                <p style={{ color: 'var(--text2)', fontSize: 12 }}>Average Confidence</p>
              </div>
              <div className="card" style={{ textAlign: 'center' }}>
                <p style={{ fontSize: 28, fontWeight: 700, color: 'var(--accent)', fontFamily: 'var(--mono)' }}>
                  {verifiedFindings.filter(v => v.supported === 'yes').length}/{verifiedFindings.length}
                </p>
                <p style={{ color: 'var(--text2)', fontSize: 12 }}>Claims Fully Supported</p>
              </div>
            </div>
            {verifiedFindings.map((f, i) => (
              <div key={i} className="card">
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                  <p style={{ fontWeight: 500, fontSize: 13, flex: 1 }}>{f.claim}</p>
                  <span className={`badge badge-${f.supported === 'yes' ? 'low' : f.supported === 'partial' ? 'medium' : 'high'}`}>
                    {f.supported}
                  </span>
                </div>
                <div style={{ marginTop: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 11, color: 'var(--text3)' }}>Confidence</span>
                    <span style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>
                      {Math.round((f.confidence_score || 0) * 100)}%
                    </span>
                  </div>
                  <div style={{ height: 4, background: 'var(--bg3)', borderRadius: 2 }}>
                    <div style={{
                      height: '100%', borderRadius: 2,
                      width: `${(f.confidence_score || 0) * 100}%`,
                      background: f.confidence_score > 0.7 ? 'var(--success)' : f.confidence_score > 0.4 ? 'var(--warn)' : 'var(--danger)',
                    }} />
                  </div>
                </div>
                {f.best_source && (
                  <a href={f.best_source} target="_blank" rel="noopener noreferrer"
                    style={{ display: 'block', marginTop: 8, fontSize: 11, color: 'var(--accent)', textDecoration: 'none' }}>
                    → {f.best_source.slice(0, 70)}...
                  </a>
                )}
                {f.contradiction && (
                  <p style={{ marginTop: 8, fontSize: 12, color: 'var(--warn)', padding: '6px 10px', background: 'rgba(245,158,11,0.08)', borderRadius: 6 }}>
                    ⚠ {f.contradiction}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {/* CHAT TAB */}
        {activeTab === 'chat' && (
          <div className="card">
            <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
              <MessageSquare size={15} color="var(--accent)" /> Ask Phi-3 About This Research
            </h3>
            <p style={{ color: 'var(--text3)', fontSize: 12, marginBottom: 16 }}>
              Answers are grounded in verified evidence from this session. Running locally via Ollama.
            </p>
            <ChatPanel sessionId={sessionId} />
          </div>
        )}
      </div>
    </div>
  );
}
