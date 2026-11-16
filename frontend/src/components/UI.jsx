import React from 'react'
import { AlertCircle, ArrowRight, FileSearch, LoaderCircle } from 'lucide-react'

export function Status({ value, small = false }) {
  const name = (value || 'undetermined').replaceAll('_', ' ')
  return <span className={`status status-${value || 'neutral'} ${small ? 'status-small' : ''}`}><span className="status-dot" />{name}</span>
}

export function PageHeader({ eyebrow, title, description, action }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{description && <p>{description}</p>}</div>{action && <div className="heading-action">{action}</div>}</div>
}

export function Empty({ title, text, action, icon: Icon = FileSearch }) {
  return <div className="empty"><div className="empty-icon"><Icon size={25} /></div><h3>{title}</h3><p>{text}</p>{action}</div>
}

export function Loading({ text = 'Loading workspace…' }) {
  return <div className="loading"><LoaderCircle className="spin" size={22} />{text}</div>
}

export function ErrorNotice({ message, onClose }) {
  if (!message) return null
  return <div className="error-notice" role="alert"><AlertCircle size={18} /><span>{message}</span>{onClose && <button className="icon-button" onClick={onClose} aria-label="Close error">×</button>}</div>
}

export function InfoLine({ children }) { return <div className="info-line"><AlertCircle size={15} />{children}</div> }
export function ArrowLink({ children }) { return <span className="arrow-link">{children}<ArrowRight size={15} /></span> }
