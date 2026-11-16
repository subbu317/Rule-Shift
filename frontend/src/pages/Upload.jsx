import React, { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, CheckCircle2, FileCheck2, FileUp, Info, LoaderCircle, ShieldCheck, UploadCloud, X } from 'lucide-react'
import { post } from '../api.js'
import { ErrorNotice, InfoLine, PageHeader } from '../components/UI.jsx'

function Dropzone({ label, sub, file, onFile, dark }) {
  const ref = useRef(null)
  const [drag, setDrag] = useState(false)
  const selected = incoming => { if (incoming) onFile(incoming) }
  return <div className={`dropzone ${drag ? 'dragging' : ''} ${file ? 'has-file' : ''} ${dark ? 'dropzone-dark' : ''}`} onDragOver={e => { e.preventDefault(); setDrag(true) }} onDragLeave={e => { e.preventDefault(); setDrag(false) }} onDrop={e => { e.preventDefault(); setDrag(false); selected(e.dataTransfer.files?.[0]) }}>
    <input aria-label={`Select ${label} PDF`} ref={ref} type="file" accept="application/pdf,.pdf" hidden onChange={e => selected(e.target.files?.[0])} />
    <div className="drop-label">{label}<span>{sub}</span></div>
    {file ? <div className="drop-loaded"><div className="loaded-icon"><FileCheck2 size={29}/></div><div className="loaded-name" title={file.name}>{file.name}</div><small>{(file.size / 1024).toFixed(1)} KB · PDF selected</small><button type="button" className="drop-remove" onClick={() => { onFile(null); if (ref.current) ref.current.value = '' }}><X size={15}/>Remove</button></div> : <button type="button" className="drop-internal" onClick={() => ref.current?.click()}><div className="drop-cloud"><UploadCloud size={29}/></div><strong>Drop your PDF here</strong><span>or <u>browse files</u> on your device</span><small>Text-based PDF · Up to 12 MB</small></button>}
    {file && <button className="replace-file" onClick={() => ref.current?.click()}>Replace file</button>}
  </div>
}

export default function Upload() {
  const [oldFile, setOldFile] = useState(null)
  const [newFile, setNewFile] = useState(null)
  const [name, setName] = useState('')
  const [oldLabel, setOldLabel] = useState('Previous policy')
  const [newLabel, setNewLabel] = useState('Updated policy')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()
  async function submit(e) {
    e.preventDefault(); setError('')
    if (!oldFile || !newFile) return setError('Choose both PDF versions.')
    if (!oldFile.name.toLowerCase().endsWith('.pdf') || !newFile.name.toLowerCase().endsWith('.pdf')) return setError('Both files must be PDFs.')
    const form = new FormData()
    form.append('name', name.trim()); form.append('old_label', oldLabel); form.append('new_label', newLabel)
    form.append('old_file', oldFile); form.append('new_file', newFile)
    setBusy(true)
    try { const result = await post('/policies/upload-pair', form); navigate(`/compare?policy=${result.policy.id}&old=${result.old_version_id}&new=${result.new_version_id}`) }
    catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return <><PageHeader eyebrow="DOCUMENT INGESTION / STEP 01" title="Start a policy comparison." description="Upload two text-based versions of the same policy. Each original passage is retained with its page number." />
    <div className="upload-container"><div className="panel upload-panel"><div className="section-top"><div className="section-number">01</div><div><h3>Policy details</h3><p>Give this analysis a recognizable name.</p></div></div><label className="form-label">Policy name<span>*</span><input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Student Advancement Support Scheme" maxLength={180} required /></label>
      <div className="divider-space"/><div className="section-top"><div className="section-number">02</div><div><h3>Compare two versions</h3><p>PDF text extraction and deterministic clause matching happen automatically.</p></div></div>
      <div className="upload-grid"><div><label className="form-label">Previous version label<input value={oldLabel} onChange={e => setOldLabel(e.target.value)} maxLength={100}/></label><Dropzone label="PREVIOUS VERSION" sub="Version A" file={oldFile} onFile={setOldFile} /></div><div><label className="form-label">Updated version label<input value={newLabel} onChange={e => setNewLabel(e.target.value)} maxLength={100}/></label><Dropzone label="UPDATED VERSION" sub="Version B" file={newFile} onFile={setNewFile} dark /></div></div>
      <ErrorNotice message={error} onClose={() => setError('')} />
      <div className="upload-bottom"><div className="upload-privacy"><ShieldCheck size={19}/><span>Stored locally · No external AI service</span></div><button disabled={busy || !name.trim() || !oldFile || !newFile || !oldLabel.trim() || !newLabel.trim()} className="btn btn-primary btn-large" onClick={submit}>{busy ? <><LoaderCircle className="spin" size={18}/>Processing PDFs…</> : <>Analyze policy changes <ArrowRight size={18}/></>}</button></div>
    </div><div className="upload-side"><div className="panel side-advice"><div className="side-advice-icon"><Info size={18}/></div><h4>Try the sample corpus</h4><p>Use the included files to explore the complete workflow:</p><code>samples/student_aid_old.pdf</code><code>samples/student_aid_new.pdf</code><p>These are synthetic demonstration policies, not official documents.</p></div>
    <div className="panel side-advice"><div className="side-advice-icon green"><CheckCircle2 size={18}/></div><h4>Supported extraction</h4><p>Age, degree level, marks, income, categories, application dates and required documents. Unclear text is flagged, not guessed.</p></div></div></div>
  </>
}
