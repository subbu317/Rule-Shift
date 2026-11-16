import React, { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AlertTriangle, Check, CheckCircle2, ChevronDown, FileText, Plus, Save, ShieldCheck, Trash2, X } from 'lucide-react'
import { get, patch, post, remove } from '../api.js'
import EvidenceViewer from '../components/EvidenceViewer.jsx'
import { Empty, ErrorNotice, Loading, PageHeader, Status } from '../components/UI.jsx'

const OPTIONS = {
  age: ['between', { min: 18, max: 25, as_of: '2026-07-01' }],
  education_level: ['at_least', { level: 'bachelor' }],
  marks: ['min', { number: 60 }],
  annual_income: ['max', { number: 800000 }],
  category: ['in', { items: ['General', 'OBC'] }],
  application_date: ['by', { date: '2026-08-31' }],
  documents: ['all_of', { items: ['identity proof'] }],
}
const FIELD_OPTIONS = Object.keys(OPTIONS)
const OPERATORS = { age: ['between'], education_level: ['at_least'], marks: ['min', 'max'], annual_income: ['min', 'max'], category: ['in'], application_date: ['by'], documents: ['all_of'] }

function Editor({ selected, clause, versionId, onSaved, cancel, newRule = false }) {
  const [field, setField] = useState(selected?.field || 'age')
  const [operator, setOperator] = useState(selected?.operator || 'between')
  const [value, setValue] = useState(JSON.stringify(selected?.value || OPTIONS.age[1], null, 2))
  const [evidence, setEvidence] = useState(selected?.evidence_text || clause?.text || '')
  const [status, setStatus] = useState(selected?.status || 'accepted')
  const [note, setNote] = useState(selected?.reviewer_note || '')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { const f = selected?.field || 'age'; setField(f); setOperator(selected?.operator || OPTIONS[f][0]); setValue(JSON.stringify(selected?.value || OPTIONS[f][1], null, 2)); setEvidence(selected?.evidence_text || clause?.text || ''); setStatus(selected?.status || 'accepted'); setNote(selected?.reviewer_note || ''); setError('') }, [selected?.id, clause?.id, newRule])
  function changeField(next) { setField(next); setOperator(OPTIONS[next][0]); setValue(JSON.stringify(OPTIONS[next][1], null, 2)) }
  async function save(e) {
    e.preventDefault(); setBusy(true); setError('')
    try {
      const body = { field, operator, value: JSON.parse(value), evidence_text: evidence, status, reviewer_note: note }
      if (newRule) await post(`/versions/${versionId}/clauses/${clause.id}/rules`, body)
      else await patch(`/rules/${selected.id}`, body)
      onSaved()
    } catch (err) { setError(err instanceof SyntaxError ? 'Invalid JSON rule value.' : err.message) } finally { setBusy(false) }
  }
  return <form onSubmit={save} className="rule-editor"><div className="panel-heading"><div><h3>{newRule ? 'Manually extract a rule' : 'Review extracted rule'}</h3><p>All accepted rules must cite an exact source substring.</p></div><button type="button" className="icon-button" onClick={cancel} aria-label="Close editor"><X size={19}/></button></div>
    <div className="form-grid"><label className="form-label">Applicant field<select value={field} onChange={e => changeField(e.target.value)}>{FIELD_OPTIONS.map(o => <option key={o}>{o}</option>)}</select></label><label className="form-label">Operator<select value={operator} onChange={e => setOperator(e.target.value)}>{OPERATORS[field].map(o => <option key={o}>{o}</option>)}</select></label><label className="form-label span-2">Structured rule value (JSON)<textarea rows={5} spellCheck="false" value={value} onChange={e => setValue(e.target.value)} className="code-textarea" /></label><label className="form-label span-2">Exact source quote<textarea rows={4} value={evidence} onChange={e => setEvidence(e.target.value)} /></label><label className="form-label">Review status<select value={status} onChange={e => setStatus(e.target.value)}><option value="accepted">Accepted</option><option value="pending">Pending</option><option value="rejected">Rejected</option></select></label><label className="form-label">Reviewer note<input value={note} onChange={e => setNote(e.target.value)} placeholder="Why this interpretation?" maxLength={1500}/></label></div>
    <ErrorNotice message={error}/><div className="form-submit-row"><span>Manual changes are auditable and can affect simulations.</span><button type="submit" disabled={busy} className="btn btn-primary"><Save size={17}/>{busy ? 'Saving…' : 'Save reviewed rule'}</button></div>
  </form>
}

export default function Review() {
  const [query] = useSearchParams()
  const [policies, setPolicies] = useState(null)
  const [versionId, setVersionId] = useState(query.get('version') || '')
  const [version, setVersion] = useState(null)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null)
  const [newRuleClause, setNewRuleClause] = useState(null)
  const [selectedClause, setSelectedClause] = useState(null)
  useEffect(() => { get('/policies').then(p => { setPolicies(p); if (!query.get('version')) setVersionId(String(p[0]?.versions?.at(-1)?.id || '')) }).catch(e => setError(e.message)) }, [])
  useEffect(() => { if (!versionId) return; get(`/versions/${versionId}`).then(v => { setVersion(v); setEditing(null); setNewRuleClause(null); setSelectedClause(v.clauses[0]?.id || null) }).catch(e => setError(e.message)) }, [versionId])
  const versionList = policies?.flatMap(p => p.versions.map(v => ({ ...v, policyName: p.name }))) || []
  const activeClause = version?.clauses.find(c => c.id === selectedClause) || version?.clauses[0]
  const activeRules = version?.rules.filter(r => r.clause_id === activeClause?.id) || []
  const editingRule = activeRules.find(r => r.id === editing)
  const warningList = version?.warnings || []
  const load = async () => { const data = await get(`/versions/${versionId}`); setVersion(data); setEditing(null); setNewRuleClause(null) }
  async function deleteRule(r) {
    if (!window.confirm('Delete this rule permanently? This can change a simulation result.')) return
    try { await remove(`/rules/${r.id}`); await load() } catch (e) { setError(e.message) }
  }
  return <><PageHeader eyebrow="HUMAN-IN-THE-LOOP / REVIEW" title="Review extracted rules" description="Correct deterministic extraction, reject unsupported interpretations, or add an evidence-linked rule manually." />
    <ErrorNotice message={error}/><section className="panel review-select"><div className="review-select-description"><ShieldCheck size={22}/><div><h3>Review a document version</h3><p>All changes are stored locally and used in the next simulation.</p></div></div><label className="form-label">Policy version<select value={versionId} onChange={e => { setVersionId(e.target.value); setVersion(null) }}><option value="">Choose version</option>{versionList.map(v => <option key={v.id} value={v.id}>{v.policyName} · {v.label}</option>)}</select></label></section>
    {!versionId ? <div className="panel"><Empty title="No policy versions yet" text="Upload a pair of PDFs to inspect their extracted criteria." action={<Link to="/upload" className="btn btn-secondary">Upload PDFs</Link>} /></div> : !version ? <Loading /> : <>
      <div className="review-metrics"><div><strong>{version.clauses.length}</strong><span>Clauses</span></div><div><strong>{version.rules.length}</strong><span>Extracted rules</span></div><div><strong>{version.rules.filter(r => r.status === 'pending').length}</strong><span>Awaiting review</span></div><div><strong>{warningList.length}</strong><span>Document warnings</span></div></div>
      {!!warningList.length && <div className="review-warning"><AlertTriangle size={19}/><div><strong>Check these extraction limitations</strong>{warningList.map((w, i) => <p key={i}>Page {w.page}: {w.message} {w.clause ? `(Clause ${w.clause})` : ''}</p>)}</div></div>}
      <div className="review-layout"><section className="panel review-clauses"><div className="panel-heading"><div><h3>Source clauses</h3><p>Select the passage you want to audit</p></div></div><div className="review-clause-scroll">{version.clauses.map(c => <button key={c.id} className={`review-clause ${activeClause?.id === c.id ? 'selected' : ''}`} onClick={() => { setSelectedClause(c.id); setEditing(null); setNewRuleClause(null) }}><div><span>CLAUSE {c.ordinal}</span><span>{version.rules.filter(r => r.clause_id === c.id).length} rule(s)</span></div><strong>{c.heading}</strong><p>{c.text}</p></button>)}</div></section>
      <div className="review-detail"><section className="panel rule-list-panel"><div className="panel-heading"><div><h3>Extracted criteria</h3><p>Clause #{activeClause?.ordinal} · Page {activeClause?.page}</p></div><button onClick={() => { setNewRuleClause(activeClause?.id); setEditing(null) }} className="btn btn-secondary btn-small"><Plus size={16}/>Add rule</button></div>
        {activeRules.length ? activeRules.map(r => <div key={r.id} className={`rule-row ${editing === r.id ? 'active' : ''}`}><div><div className="rule-row-label"><strong>{r.field.replaceAll('_',' ')}</strong><Status value={r.status} small/>{r.manual && <span className="manual-chip">MANUAL</span>}</div><p>{r.operator} · {JSON.stringify(r.value)}</p><span>Evidence on page {r.page}</span></div><div className="rule-row-actions"><button className="btn btn-ghost btn-small" onClick={() => { setEditing(r.id); setNewRuleClause(null) }}>Review</button><button className="icon-button danger-hover" title="Delete rule" onClick={() => deleteRule(r)}><Trash2 size={16}/></button></div></div>) : <div className="mini-empty">No structured rules extracted from this clause. Add a supported rule only if the passage explicitly contains it.</div>}</section>
        {(editingRule || newRuleClause) && <section className="panel"><Editor key={`${editingRule?.id || 'new'}-${activeClause.id}`} selected={editingRule} clause={activeClause} versionId={versionId} newRule={!!newRuleClause} onSaved={load} cancel={() => { setEditing(null); setNewRuleClause(null) }} /></section>}
        <section className="panel"><EvidenceViewer versionId={Number(versionId)} clause={activeClause} label="Source clause and page" /></section></div></div>
    </>}
  </>
}
