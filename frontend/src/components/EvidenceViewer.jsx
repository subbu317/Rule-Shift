import React, { useState } from 'react'
import { ExternalLink, FileText, ZoomIn, ZoomOut } from 'lucide-react'
import { pageUrl } from '../api.js'

export default function EvidenceViewer({ versionId, clause, label = 'Source evidence' }) {
  const [zoom, setZoom] = useState(100)
  const [failed, setFailed] = useState(false)
  React.useEffect(() => { setFailed(false); setZoom(100) }, [versionId, clause?.id])
  if (!clause) return <div className="evidence-empty">Choose a clause to see the original page.</div>
  const url = pageUrl(versionId, clause.page, clause.id)
  return <div className="evidence-viewer"><div className="evidence-toolbar"><div><FileText size={17} /><strong>{label}</strong><span className="mono">PAGE {clause.page}</span></div>
    <div className="toolbar-actions"><button title="Zoom out" aria-label="Zoom out" onClick={() => setZoom(z => Math.max(70, z - 20))}><ZoomOut size={17} /></button><span>{zoom}%</span><button title="Zoom in" aria-label="Zoom in" onClick={() => setZoom(z => Math.min(180, z + 20))}><ZoomIn size={17} /></button><a href={url} target="_blank" rel="noreferrer" title="Open page preview"><ExternalLink size={16} /></a></div></div>
    <div className="evidence-paper"><div className="evidence-scroll">{failed ? <div className="image-fallback">Could not render this page. The verified text passage remains below.</div> : <img src={url} alt={`PDF page ${clause.page} with passage highlight`} style={{ width: `${zoom}%` }} onError={() => setFailed(true)} />}</div></div>
    <div className="evidence-excerpt"><strong>Extracted passage · Page {clause.page}</strong><p>{clause.text}</p></div>
  </div>
}
