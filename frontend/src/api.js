export const API = '/api'

export async function request(path, options = {}) {
  let response
  try {
    const headers = options.body instanceof FormData ? {} : options.body ? { 'Content-Type': 'application/json' } : {}
    response = await fetch(`${API}${path}`, { ...options, headers: { ...headers, ...options.headers } })
  } catch (_) {
    throw new Error('Cannot reach the local API. Start FastAPI at http://127.0.0.1:8000 and refresh.')
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const payload = await response.json()
      if (typeof payload.detail === 'string') message = payload.detail
      else if (Array.isArray(payload.detail)) message = payload.detail.map(x => `${x.loc?.join('.')}: ${x.msg}`).join('; ')
    } catch (_) { /* Keep original error */ }
    throw new Error(message)
  }
  if (response.status === 204) return null
  return response.json()
}

export const get = path => request(path)
export const post = (path, body) => request(path, { method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body) })
export const patch = (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) })
export const remove = path => request(path, { method: 'DELETE' })

export function reportUrl(oldVersion, newVersion, applicant) {
  return `${API}/reports/comparison.pdf?${new URLSearchParams({ old_version_id: oldVersion, new_version_id: newVersion, applicant_id: applicant })}`
}
export function pageUrl(versionId, page, clauseId) {
  return `${API}/versions/${versionId}/pages/${page}/image${clauseId ? `?clause_id=${clauseId}` : ''}`
}
