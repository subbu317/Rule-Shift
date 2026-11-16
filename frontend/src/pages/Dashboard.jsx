import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Activity, ArrowRight, ArrowUpRight, ClipboardCheck, FileDiff, Files, ShieldCheck, Sparkles, UsersRound, Plus, History as HistoryIcon, Layers3, DatabaseZap } from 'lucide-react'
import { get } from '../api.js'
import { Empty, ErrorNotice, Loading, PageHeader } from '../components/UI.jsx'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  useEffect(() => { get('/dashboard').then(setData).catch(e => setError(e.message)) }, [])
  const stats = [
    { label: 'Policies in library', value: data?.policies ?? '—', Icon: Files, accent: 'mint', caption: 'Tracked policy families' },
    { label: 'Policy versions', value: data?.versions ?? '—', Icon: Layers3, accent: 'blue', caption: 'Evidence-bearing PDFs' },
    { label: 'Applicant profiles', value: data?.applicants ?? '—', Icon: UsersRound, accent: 'violet', caption: 'Stored on this device' },
    { label: 'Verified rules', value: data?.rules ?? '—', Icon: ClipboardCheck, accent: 'amber', caption: 'Ready to evaluate' },
  ]
  return <>
    <PageHeader eyebrow="CONTROL CENTER / OVERVIEW" title="Policy intelligence, simplified." description="Turn policy revisions into traceable, applicant-specific eligibility decisions." action={<Link to="/upload" className="btn btn-primary"><Plus size={17} />New analysis</Link>} />
    <div className="hero-banner"><div className="hero-content"><div className="hero-kicker"><Sparkles size={14} /> EVIDENCE-GROUNDED INTELLIGENCE</div><h2>Know what changed.<br /><span>Know who it affects.</span></h2><p>Compare source clauses, simulate eligibility before and after, and audit each decision against the original PDF.</p><Link to="/upload" className="hero-cta">Start comparing <ArrowRight size={17} /></Link></div><div className="hero-art" aria-hidden="true"><div className="art-orbit art-orbit-one"/><div className="art-orbit art-orbit-two"/><div className="art-pane art-pane-left"><div className="art-pane-top"><span/>PREVIOUS</div><div className="art-line long"/><div className="art-line medium"/><div className="art-line short"/><div className="art-highlight old"><span/>60%</div><div className="art-line medium"/></div><div className="art-vs"><Activity size={24}/></div><div className="art-pane art-pane-right"><div className="art-pane-top"><span/>UPDATED</div><div className="art-line long"/><div className="art-line medium"/><div className="art-line short"/><div className="art-highlight new"><span/>65%</div><div className="art-line medium"/></div></div></div>
    <ErrorNotice message={error} />
    <section className="stats-grid">{stats.map(s => <div className="stat-card" key={s.label}><div className={`stat-icon stat-${s.accent}`}><s.Icon size={21}/></div><div className="stat-value">{s.value}</div><div className="stat-label">{s.label}</div><p>{s.caption}</p></div>)}</section>
    <div className="dashboard-grid"><section className="panel recent-panel"><div className="panel-heading"><div><h3>Recent policy analyses</h3><p>Jump back into your most recent work</p></div><Link to="/history" className="subtle-link">View library <ArrowUpRight size={16} /></Link></div>
      {!data && !error ? <Loading /> : data?.recent?.length ? <div className="recent-list">{data.recent.map(p => <button className="recent-item" key={p.id} onClick={() => navigate(`/compare?policy=${p.id}`)}><div className="recent-icon"><FileDiff size={20}/></div><div className="recent-meta"><strong>{p.name}</strong><span>{p.versions.length} version{p.versions.length !== 1 ? 's' : ''} · Added {new Date(p.created_at).toLocaleDateString()}</span></div><ArrowRight size={18} /></button>)}</div> : <Empty title="Your workspace is ready" text="Upload two sample policy PDFs to run your first comparison." action={<Link className="btn btn-secondary" to="/upload">Upload a policy</Link>} />}</section>
      <section className="panel process-panel"><div className="panel-heading"><div><h3>How your evidence flows</h3><p>Every step is transparent and locally executed</p></div><ShieldCheck size={20} className="text-mint" /></div>
        <div className="pipeline"><div><div className="pipe-icon"><Files size={18}/></div><div><strong>01 / Extract</strong><span>Text and source-page references</span></div></div><div><div className="pipe-icon"><FileDiff size={18}/></div><div><strong>02 / Compare</strong><span>Aligned clauses and rule changes</span></div></div><div><div className="pipe-icon"><DatabaseZap size={18}/></div><div><strong>03 / Simulate</strong><span>Deterministic eligibility checks</span></div></div><div><div className="pipe-icon"><ClipboardCheck size={18}/></div><div><strong>04 / Verify</strong><span>Evidence, missing fields and PDF report</span></div></div></div>
        <Link to="/review" className="process-footer">Open human review workspace <ArrowRight size={16}/></Link></section></div>
  </>
}
