import React, { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AlertTriangle, ArrowDownRight, ArrowRight, ArrowUpRight, CheckCircle2, ChevronRight, ClipboardList, Download, FileDiff, FileText, Filter, GitCompareArrows, Info, Layers, LoaderCircle, Search, ShieldAlert, Sparkles, UsersRound } from 'lucide-react'
import { get, post, reportUrl } from '../api.js'
import { Empty, ErrorNotice, InfoLine, Loading, PageHeader, Status } from '../components/UI.jsx'
import EvidenceViewer from '../components/EvidenceViewer.jsx'

function Outcome({ side, label, value }) {
  const stats = { eligible: ['Meets known requirements', 'check'], ineligible: ['One or more checked requirements fail', 'x'], undetermined: ['Additional evidence or inputs needed', 'unknown'] }
  const [subtitle] = stats[value?.status] || stats.undetermined
  return <div className={`outcome-card outcome-${value?.status || 'undetermined'}`}><div className="outcome-top"><span>{label}</span><span className="outcome-mini">{side}</span></div><div className="outcome-main"><Status value={value?.status}/><h3>{value?.status === 'eligible' ? 'Eligible' : value?.status === 'ineligible' ? 'Ineligible' : 'Undetermined'}</h3><p>{subtitle}</p></div><div className="outcome-bottom">{value?.evaluated_rule_count ?? 0} verified rules checked</div></div>
}

export default function Comparison() {
  const [query] = useSearchParams()
  const [policies, setPolicies] = useState(null)
  const [applicants, setApplicants] = useState(null)
  const [policyId, setPolicyId] = useState(query.get('policy') || '')
  const [oldId, setOldId] = useState(query.get('old') || '')
  const [newId, setNewId] = useState(query.get('new') || '')
  const [applicantId, setApplicantId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [active, setActive] = useState(null)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [evidenceSide, setEvidenceSide] = useState('new')
  useEffect(() => { Promise.all([get('/policies'), get('/applicants')]).then(([p, a]) => {
    setPolicies(p); setApplicants(a)
    if (!query.get('policy') && p.length) { setPolicyId(String(p[0].id)); setOldId(String(p[0].versions[0]?.id || '')); setNewId(String(p[0].versions.at(-1)?.id || '')) }
    if (a.length) setApplicantId(String(a[0].id))
  }).catch(e => setError(e.message)) }, [])
  const policy = policies?.find(p => String(p.id) === String(policyId))
  const versions = policy?.versions || []
  const canRun = !!(oldId && newId && applicantId && oldId !== newId)
  const selected = useMemo(() => result?.comparison.clauses.find(c => ((c.new || c.old).id) === active) || null, [result, active])
  const selectedEvidence = evidenceSide === 'new' ? (selected?.new || selected?.old) : (selected?.old || selected?.new)
  const selectedVersion = selectedEvidence === selected?.new ? Number(newId) : Number(oldId)
  const visible = (result?.comparison.clauses || []).filter(item => (filter === 'all' || item.status === filter) && (!search || ((item.old?.text || '') + (item.new?.text || '')).toLowerCase().includes(search.toLowerCase())))
  async function run(e) {
    e?.preventDefault(); setBusy(true); setError(''); setResult(null); setActive(null)
    try { const value = await post('/simulations', { old_version_id: Number(oldId), new_version_id: Number(newId), applicant_id: Number(applicantId) }); setResult(value); const focus = value.comparison.clauses.find(c => c.status === 'modified') || value.comparison.clauses[0]; setActive((focus?.new || focus?.old)?.id) }
    catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  function choosePolicy(id) {
    const found = policies.find(p => String(p.id) === id)
    setPolicyId(id); setOldId(String(found?.versions[0]?.id || '')); setNewId(String(found?.versions.at(-1)?.id || '')); setResult(null)
  }
  return <><PageHeader eyebrow="COUNTERFACTUAL ENGINE / SIMULATION" title="Compare. Understand. Decide." description="Explore each amendment and see whether it changes a specific applicant's eligibility." action={<Link className="btn btn-secondary" to="/upload"><Layers size={16}/>New upload</Link>} />
    <ErrorNotice message={error} onClose={() => setError('')} />
    <section className="panel selector-panel"><div className="selector-heading"><div className="selector-symbol"><GitCompareArrows size={21}/></div><div><h3>Analysis configuration</h3><p>Select policy versions and an applicant profile</p></div></div>
      <form className="selector-form" onSubmit={run}><label className="form-label">Policy family<select value={policyId} onChange={e => choosePolicy(e.target.value)}><option value="">Choose policy</option>{policies?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <label className="form-label">Previous version<select value={oldId} onChange={e => { setOldId(e.target.value); setResult(null) }}><option value="">Choose previous</option>{versions.map(v => <option key={v.id} value={v.id}>{v.label} · #{v.id}</option>)}</select></label>
        <label className="form-label">Updated version<select value={newId} onChange={e => { setNewId(e.target.value); setResult(null) }}><option value="">Choose updated</option>{versions.map(v => <option key={v.id} value={v.id}>{v.label} · #{v.id}</option>)}</select></label>
        <label className="form-label">Applicant<select value={applicantId} onChange={e => { setApplicantId(e.target.value); setResult(null) }}><option value="">Choose applicant</option>{applicants?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <button disabled={!canRun || busy} className="btn btn-primary selector-button" type="submit">{busy ? <><LoaderCircle className="spin" size={18}/>Simulating…</> : <><Sparkles size={18}/>Run simulation</>}</button></form>
      {(!policies?.length || !applicants?.length) && <InfoLine>Requires at least one uploaded policy with two versions and one <Link to="/profiles">applicant profile</Link>. You can start with the bundled sample PDFs.</InfoLine>}</section>
    {!result ? <section className="panel initial-result"><Empty icon={FileDiff} title="Ready for a clearer answer" text="Choose a policy, both versions and an applicant, then run the evidence-grounded simulation." action={<Link className="btn btn-secondary" to="/profiles"><UsersRound size={16}/>Manage profiles</Link>} /></section> : <>
      <div className="simulation-title"><div><div className="eyebrow">RESULTS / {result.applicant_name}</div><h2>Eligibility evolution</h2></div><a href={reportUrl(oldId, newId, applicantId)} className="btn btn-secondary"><Download size={17}/>Download PDF report</a></div>
      <div className="outcome-grid"><Outcome side="VERSION A" label={result.old_label} value={result.before}/><div className="outcome-between"><ArrowRight size={21}/></div><Outcome side="VERSION B" label={result.new_label} value={result.after}/></div>
      <div className={`decision-banner ${result.eligibility_changed ? 'decision-changed' : 'decision-unchanged'}`}><div className="decision-icon">{result.eligibility_changed ? <GitCompareArrows size={21}/> : <CheckCircle2 size={21}/>}</div><div><h3>{result.eligibility_changed ? 'The overall eligibility status changed' : 'The overall eligibility status stayed the same'}</h3><p>{result.eligibility_changed ? 'Review the applicant-specific rule impacts below for the evidence behind the change.' : 'Text may have changed without changing this applicant’s status.'}</p></div><Status value={result.after.status} small/></div>
      <div className="impact-section"><div className="content-section-heading"><div><h2>Rules affecting this applicant</h2><p>Changed fields where the applicant-level rule outcome differs between versions.</p></div><span className="count-chip">{result.applicant_impacts.length} outcome changes</span></div>
        {result.applicant_impacts.length ? <div className="impact-grid">{result.applicant_impacts.map((impact, i) => <button key={`${impact.field}-${i}`} className="impact-card" onClick={() => { setActive((impact.new_clause || impact.old_clause).id); setEvidenceSide(impact.new_clause ? 'new' : 'old'); document.getElementById('comparison-evidence')?.scrollIntoView({ behavior: 'smooth' }) }}><div className="impact-card-top"><span>{impact.field.replaceAll('_', ' ')}</span><span className="impact-type">{impact.change_type}</span></div><div className="impact-states"><Status value={impact.before} small/><ArrowRight size={17}/><Status value={impact.after} small/></div><p>{(impact.new_clause || impact.old_clause)?.text}</p><div className="impact-card-bottom">View source evidence <ArrowUpRight size={16}/></div></button>)}</div> : <div className="panel no-impact"><CheckCircle2 size={20}/><span>No changed rule altered this applicant’s checked field outcomes.</span></div>}
      </div>
      {(result.before.missing_fields.length > 0 || result.after.missing_fields.length > 0 || result.before.warnings.length > 0 || result.after.warnings.length > 0 || result.before.conflicts.length > 0 || result.after.conflicts.length > 0) && <div className="panel uncertainty-panel"><div className="uncertainty-header"><ShieldAlert size={20}/><strong>Uncertainty & review flags</strong></div><div className="uncertainty-items">{[['Previous', result.before], ['Updated', result.after]].map(([label, status]) => <div key={label}><strong>{label} version</strong>{status.missing_fields.map(x => <p key={x}>Missing applicant field: {x}</p>)}{status.conflicts.map((x, i) => <p key={i}>Conflict: {x.message}</p>)}{status.warnings.map((x, i) => <p key={i}>Page {x.page}: {x.message}</p>)}</div>)}</div></div>}
      <section className="panel clause-panel" id="comparison-evidence"><div className="panel-heading"><div><h3>Clause-by-clause comparison</h3><p>Matched policy passages with exact page references</p></div><div className="counts-list">{Object.entries(result.comparison.counts).map(([k, n]) => <span className={`count-tag count-${k}`} key={k}>{n} {k}</span>)}</div></div>
        <div className="comparison-tools"><div className="filter-list">{['all', 'modified', 'added', 'removed', 'unchanged'].map(f => <button key={f} onClick={() => setFilter(f)} className={`filter-button ${filter === f ? 'selected' : ''}`}>{f[0].toUpperCase() + f.slice(1)}</button>)}</div><label className="search-input"><Search size={16}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search clause text" /></label></div>
        <div className="comparison-workspace"><div className="clause-list">{visible.length ? visible.map((c, index) => <button key={`${c.old?.id || 'x'}-${c.new?.id || 'x'}`} onClick={() => { setActive((c.new || c.old).id); setEvidenceSide(c.new ? 'new' : 'old') }} className={`clause-list-item ${active === (c.new || c.old).id ? 'selected' : ''}`}><div className="clause-heading"><Status value={c.status} small/><span>#{(c.new || c.old).ordinal}</span></div><strong>{(c.new || c.old).heading || `Clause ${index + 1}`}</strong><p>{(c.new || c.old).text}</p><span className="clause-page">P. {(c.new || c.old).page}<ChevronRight size={15}/></span></button>) : <div className="mini-empty">No clauses match these filters.</div>}</div>
          <div className="clause-detail">{selected ? <><div className="clause-detail-header"><div><div className="eyebrow">SELECTED PASSAGE / CLAUSE #{(selected.new || selected.old).ordinal}</div><h3>{(selected.new || selected.old).heading}</h3></div><Status value={selected.status} /></div>
            <div className="side-by-side"><div className="text-compare old-text"><div><span className="text-version">PREVIOUS VERSION</span>{selected.old && <span className="page-chip">Page {selected.old.page}</span>}</div><p>{selected.old?.text || 'No matching clause in previous version.'}</p>{selected.old_rules.map(r => <div className="mini-rule" key={r.id}>{r.field}: <strong>{JSON.stringify(r.value)}</strong></div>)}</div><div className="text-compare new-text"><div><span className="text-version">UPDATED VERSION</span>{selected.new && <span className="page-chip">Page {selected.new.page}</span>}</div><p>{selected.new?.text || 'Clause removed in updated version.'}</p>{selected.new_rules.map(r => <div className="mini-rule" key={r.id}>{r.field}: <strong>{JSON.stringify(r.value)}</strong></div>)}</div></div>
            <div className="evidence-choice"><span><FileText size={16}/> ORIGINAL PDF EVIDENCE</span><div className="segmented-buttons"><button className={evidenceSide === 'old' ? 'selected' : ''} onClick={() => setEvidenceSide('old')} disabled={!selected.old}>Previous</button><button className={evidenceSide === 'new' ? 'selected' : ''} onClick={() => setEvidenceSide('new')} disabled={!selected.new}>Updated</button></div></div>
            <EvidenceViewer versionId={selectedVersion} clause={selectedEvidence} label={evidenceSide === 'new' ? 'Updated PDF page' : 'Previous PDF page'} /></> : <Empty title="Select a clause" text="Click a clause on the left to see changes and original-source evidence." />}</div></div></section>
      <div className="result-disclaimer"><Info size={17}/>{result.disclaimer}</div>
    </>}
  </>
}
