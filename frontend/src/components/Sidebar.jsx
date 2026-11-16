import React from 'react'
import { NavLink } from 'react-router-dom'
import { Activity, ArrowUpRight, BookOpen, FileDiff, History, LayoutDashboard, PanelLeftClose, PlusCircle, ShieldCheck, UsersRound, X } from 'lucide-react'

const links = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/upload', label: 'Upload policies', icon: PlusCircle },
  { to: '/compare', label: 'Compare & simulate', icon: FileDiff },
  { to: '/profiles', label: 'Applicant profiles', icon: UsersRound },
  { to: '/review', label: 'Rule review', icon: ShieldCheck },
  { to: '/history', label: 'Policy library', icon: History },
]

export default function Sidebar({ open, onClose }) {
  return <>
    {open && <div className="mobile-overlay" onClick={onClose} />}
    <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-logo"><Activity size={24} strokeWidth={2.6} /></div>
        <div className="brand-text"><strong>RuleShift<span className="brand-period">.</span></strong><small>POLICY INTELLIGENCE</small></div>
        <button className="mobile-close" onClick={onClose} aria-label="Close navigation"><X size={20} /></button>
      </div>
      <div className="nav-label">WORKSPACE</div>
      <nav className="nav-list" aria-label="Main navigation">
        {links.map(({ to, label, icon: Icon }) => <NavLink onClick={onClose} key={to} to={to} end={to === '/'} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Icon size={19} /><span>{label}</span>{to === '/upload' && <ArrowUpRight className="nav-trailing" size={15} />}</NavLink>)}
      </nav>
      <div className="sidebar-bottom"><div className="privacy-panel"><div className="privacy-icon"><ShieldCheck size={18} /></div><strong>Private by design</strong><p>Your PDFs and profiles stay in your local workspace. No cloud or paid AI needed.</p></div>
        <a className="docs-link" href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer"><BookOpen size={17} />API documentation<ArrowUpRight size={15} /></a>
        <div className="sidebar-foot"><span className="online-dot" />LOCAL WORKSPACE <span className="foot-version">v1.0</span></div></div>
    </aside>
  </>
}
