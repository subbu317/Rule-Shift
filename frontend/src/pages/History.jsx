import React, { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Clock3, FileText, FolderArchive, History as HistoryIcon, Plus, Search, Trash2 } from 'lucide-react'
import { get, remove } from '../api.js'
import { Empty, ErrorNotice, Loading, PageHeader } from '../components/UI.jsx'

export default function History() {
  const [records, setRecords] = useState(null)
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const load = useCallback((needle = '') => get(`/policies?search=${encodeURIComponent(needle)}`).then(setRecords).catch(e => setError(e.message)), [])
  useEffect(() => { const timer = setTimeout(() => load(query), 200); return () => clearTimeout(timer) }, [query, load])
  async function forget(policy) {
    if (!window.confirm(`Delete “${policy.name}” and all its PDF versions, extracted clauses and rules? This is permanent.`)) return
    try { await remove(`/policies/${policy.id}`); await load(query) }
    catch (err) { setError(err.message) }
  }
  return <><PageHeader eyebrow="DOCUMENT LIBRARY / HISTORY" title="Your policy library" description="Search stored policy families, inspect their version histories and revisit comparisons." action={<Link to="/upload" className="btn btn-primary"><Plus size={17}/>Upload policy</Link>} />
    <ErrorNotice message={error}/><section className="panel history-panel"><div className="history-heading"><div><h3>Uploaded policies</h3><p>{records ? records.length : '—'} matches</p></div><label className="search-input"><Search size={18}/><input placeholder="Search policies..." value={query} onChange={e => setQuery(e.target.value)}/></label></div>
      {records === null ? <Loading /> : records.length ? <div className="history-grid">{records.map(p => <div key={p.id} className="history-card"><div className="history-card-head"><div className="history-icon"><FolderArchive size={24}/></div><button title="Delete this policy family" className="icon-button danger-hover" onClick={() => forget(p)}><Trash2 size={17}/></button></div><h3>{p.name}</h3><div className="history-date"><Clock3 size={14}/>Created {new Date(p.created_at).toLocaleDateString()}</div><div className="history-versions">{p.versions.map(v => <div key={v.id}><FileText size={16}/><span>{v.label}<small>{v.page_count} page{v.page_count !== 1 ? 's' : ''} · {v.filename}</small></span></div>)}</div><div className="history-actions"><Link className="btn btn-secondary btn-small" to={`/review?version=${p.versions.at(-1)?.id}`}><FileText size={15}/>Review rules</Link><button className="btn btn-text btn-small" onClick={() => navigate(`/compare?policy=${p.id}`)}>Open analysis <ArrowRight size={16}/></button></div></div>)}</div> : <Empty icon={HistoryIcon} title={query ? 'No matching policies' : 'Nothing uploaded yet'} text={query ? 'Try another search term.' : 'Upload two policy versions to start building your local history.'} action={!query && <Link to="/upload" className="btn btn-secondary">Upload PDFs</Link>} />}</section>
  </>
}
