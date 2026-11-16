import React, { useCallback, useEffect, useState } from 'react'
import { Check, Edit3, Plus, Save, Trash2, UserRound, UserRoundPlus, X } from 'lucide-react'
import { get, patch, post, remove } from '../api.js'
import { Empty, ErrorNotice, Loading, PageHeader } from '../components/UI.jsx'

const EMPTY = { name: '', date_of_birth: '', education_level: '', marks: '', annual_income: '', category: '', application_date: '', documents: '' }
const LABELS = [
  { key: 'date_of_birth', label: 'Date of birth', type: 'date' },
  { key: 'education_level', label: 'Education level', options: [['class10', 'Class 10'], ['class12', 'Class 12'], ['diploma', 'Diploma'], ['bachelor', "Bachelor's degree"], ['master', "Master's degree"], ['doctorate', 'Doctorate']] },
  { key: 'marks', label: 'Qualifying marks (%)', type: 'number', min: 0, max: 100, step: '0.01' },
  { key: 'annual_income', label: 'Annual family income (INR)', type: 'number', min: 0, step: '1' },
  { key: 'category', label: 'Category', options: ['General', 'OBC', 'SC', 'ST', 'EWS', 'Other'].map(x => [x, x]) },
  { key: 'application_date', label: 'Application submission date', type: 'date' },
  { key: 'documents', label: 'Available documents (comma-separated)', type: 'text', placeholder: 'identity proof, degree certificate, income certificate' },
]

function toPayload(values) {
  const fields = { ...values }
  delete fields.name
  for (const key of Object.keys(fields)) if (fields[key] === '') fields[key] = null
  for (const key of ['marks', 'annual_income']) if (fields[key] !== null) fields[key] = Number(fields[key])
  if (fields.documents != null) fields.documents = fields.documents.split(',').map(s => s.trim()).filter(Boolean)
  return { name: values.name.trim(), details: fields }
}
function fromRecord(record) { return { name: record.name, ...Object.fromEntries(Object.entries(record.details).map(([k, v]) => [k, Array.isArray(v) ? v.join(', ') : v == null ? '' : String(v)])) } }

export default function Profiles() {
  const [profiles, setProfiles] = useState(null)
  const [editing, setEditing] = useState(null)
  const [values, setValues] = useState(EMPTY)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)
  const load = useCallback(() => get('/applicants').then(setProfiles).catch(e => setError(e.message)), [])
  useEffect(() => { load() }, [load])
  const update = (field, value) => setValues(v => ({ ...v, [field]: value }))
  async function save(e) {
    e.preventDefault(); setBusy(true); setError(''); setSuccess('')
    try {
      if (editing) await patch(`/applicants/${editing}`, toPayload(values)); else await post('/applicants', toPayload(values))
      setEditing(null); setValues(EMPTY); setSuccess('Profile saved locally.'); await load()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  async function deleteOne(profile) {
    if (!window.confirm(`Permanently delete the local profile “${profile.name}”?`)) return
    try { await remove(`/applicants/${profile.id}`); if (editing === profile.id) { setEditing(null); setValues(EMPTY) } await load() }
    catch (err) { setError(err.message) }
  }
  return <><PageHeader eyebrow="APPLICANT DATA / LOCAL ONLY" title="Applicant profiles" description="Create realistic profiles to simulate how policy amendments affect different people. Leave unknown fields empty." />
    <ErrorNotice message={error} onClose={() => setError('')} />{success && <div className="success-notice"><Check size={18}/>{success}</div>}
    <div className="profile-layout"><section className="panel profile-list"><div className="panel-heading"><div><h3>Saved profiles</h3><p>{profiles?.length ?? '—'} local records</p></div><button className="btn btn-ghost btn-small" onClick={() => { setEditing(null); setValues(EMPTY); setSuccess('') }}><Plus size={16}/> New</button></div>
      {!profiles ? <Loading /> : profiles.length === 0 ? <Empty icon={UserRoundPlus} title="No profiles yet" text="Use the form to create your first applicant." /> : <div className="profiles-items">{profiles.map(p => <div className={`profile-item ${p.id === editing ? 'selected' : ''}`} key={p.id}><div className="profile-avatar"><UserRound size={20}/></div><div className="profile-data"><strong>{p.name}</strong><span>{p.details.education_level || 'Education unknown'} · {p.details.marks == null ? 'Marks unknown' : `${p.details.marks}% marks`}</span></div><button className="icon-button" title="Edit profile" onClick={() => { setEditing(p.id); setValues(fromRecord(p)); setSuccess('') }}><Edit3 size={17}/></button><button className="icon-button danger-hover" title="Delete profile" onClick={() => deleteOne(p)}><Trash2 size={17}/></button></div>)}</div>}</section>
    <section className="panel profile-form-panel"><div className="panel-heading"><div><h3>{editing ? 'Edit applicant' : 'Create applicant'}</h3><p>All fields except the profile label are optional</p></div><div className="form-badge">{editing ? `Editing #${editing}` : 'New record'}</div></div>
      <form onSubmit={save}><div className="form-grid"><label className="form-label span-2">Profile label <span>*</span><input value={values.name} onChange={e => update('name', e.target.value)} placeholder="e.g. Asha — scholarship scenario" required maxLength={120} /></label>
        {LABELS.map(field => <label key={field.key} className={`form-label ${field.key === 'documents' ? 'span-2' : ''}`}>{field.label}{field.options ? <select value={values[field.key]} onChange={e => update(field.key, e.target.value)}><option value="">Not provided</option>{field.options.map(([val, name]) => <option value={val} key={val}>{name}</option>)}</select> : <input type={field.type} value={values[field.key]} min={field.min} max={field.max} step={field.step} placeholder={field.placeholder} onChange={e => update(field.key, e.target.value)} />}</label>)}</div>
      <div className="form-submit-row"><span>Unknown fields yield “undetermined” where needed.</span><div>{editing && <button type="button" className="btn btn-secondary" onClick={() => { setEditing(null); setValues(EMPTY) }}><X size={16}/> Cancel</button>}<button className="btn btn-primary" disabled={busy || !values.name.trim()} type="submit"><Save size={17}/>{busy ? 'Saving…' : 'Save profile'}</button></div></div></form></section></div>
  </>
}
