import React, { useState } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import { Menu, ShieldCheck, Wifi } from 'lucide-react'
import Sidebar from './components/Sidebar.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Upload from './pages/Upload.jsx'
import Comparison from './pages/Comparison.jsx'
import Profiles from './pages/Profiles.jsx'
import Review from './pages/Review.jsx'
import History from './pages/History.jsx'

export default function App() {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  React.useEffect(() => { setOpen(false); window.scrollTo({ top: 0, behavior: 'instant' }) }, [location.pathname])
  return <div className="app-shell"><Sidebar open={open} onClose={() => setOpen(false)} />
    <main className="main-area"><header className="topbar"><div className="topbar-left"><button className="mobile-menu" onClick={() => setOpen(true)} aria-label="Open menu"><Menu size={22} /></button><span className="topbar-breadcrumb">Workspace</span><span className="crumb-chevron">/</span><strong>{({ '/': 'Overview', '/upload': 'Upload', '/compare': 'Simulation', '/profiles': 'Profiles', '/review': 'Review', '/history': 'Library' })[location.pathname] || 'Workspace'}</strong></div><div className="topbar-right"><span className="workspace-indicator"><Wifi size={15} />Local mode</span><div className="avatar">RS</div></div></header>
      <div className="content"><Routes><Route path="/" element={<Dashboard />} /><Route path="/upload" element={<Upload />} /><Route path="/compare" element={<Comparison />} /><Route path="/profiles" element={<Profiles />} /><Route path="/review" element={<Review />} /><Route path="/history" element={<History />} /><Route path="*" element={<Dashboard />} /></Routes></div>
      <footer className="footer"><span>© RuleShift · Evidence before inference.</span><span><ShieldCheck size={14} />Informational only · Not an official decision</span></footer>
    </main>
  </div>
}
