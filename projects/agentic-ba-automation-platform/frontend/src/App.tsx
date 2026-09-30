import { type FormEvent, useEffect, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

type Citation = { chunk_id: string; quote: string }
type Artifact = { id: string; type: string; content: string; status: string; revision: number; citations: Citation[]; reviewer_id?: string | null; review_comment?: string | null }
type SourceDocument = { id: string; filename: string; uploaded_at: string }
type Audit = { id: string; action: string; user_id: string; timestamp: string }

const API = apiBase(import.meta.env.VITE_API_URL ?? '/api')

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, options)
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(errorMessage(body.detail, response.status))
  return body as T
}

function App() {
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [audit, setAudit] = useState<Audit[]>([])
  const [documents, setDocuments] = useState<SourceDocument[]>([])
  const [comment, setComment] = useState('')
  const [selected, setSelected] = useState<Artifact | null>(null)
  const [query, setQuery] = useState('guest checkout payment')
  const [type, setType] = useState('user_story')
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('Seed the source-backed checkout workspace to begin.')
  const [error, setError] = useState('')

  const refresh = async () => {
    const [nextArtifacts, nextAudit, nextDocuments] = await Promise.all([
      request<Artifact[]>('/artifacts'), request<Audit[]>('/audit'), request<SourceDocument[]>('/documents'),
    ])
    setArtifacts(nextArtifacts)
    setDocuments(nextDocuments)
    setAudit(nextAudit)
    setSelected((current) => current ? nextArtifacts.find((item) => item.id === current.id) ?? null : null)
  }

  useEffect(() => { refresh().catch((reason: Error) => setError(reason.message)) }, [])

  // Open the first item once data arrives, so the detail panel is never an empty prompt.
  useEffect(() => {
    if (!selected && artifacts.length) { setSelected(artifacts[0]); setDraft(artifacts[0].content) }
    if (artifacts.length) setNotice((current) => current.startsWith('Seed the source-backed') ? 'Review the selected artifact, or generate another from the indexed sources.' : current)
  }, [artifacts, selected])

  const run = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true); setError('')
    try { await action(); await refresh(); setNotice(success) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unexpected error') }
    finally { setBusy(false) }
  }

  const seed = () => run(async () => {
    const result = await request<{ artifact: Artifact }>('/demo/seed', { method: 'POST' })
    setSelected(result.artifact); setDraft(result.artifact.content); setComment('')
  }, 'Demo evidence indexed and a grounded user story created.')

  const generate = (event: FormEvent) => {
    event.preventDefault()
    return run(async () => {
      const artifact = await request<Artifact>('/generate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, artifact_type: type, user_id: 'demo-analyst' }),
      })
      setSelected(artifact); setDraft(artifact.content); setComment('')
    }, 'New source-backed artifact is ready for review.')
  }

  const upload = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const element = event.currentTarget
    const form = new FormData(element)
    form.set('user_id', 'demo-analyst')
    return run(async () => { await request('/upload', { method: 'POST', body: form }); element.reset() }, 'Document extracted and indexed.')
  }

  // The API trims saved content, so compare trimmed text.
  const unsaved = Boolean(selected && draft.trim() !== selected.content.trim())
  const selectArtifact = (artifact: Artifact) => {
    if (artifact.id === selected?.id) return
    if (unsaved && !window.confirm('Discard unsaved changes to this artifact?')) return
    setSelected(artifact); setDraft(artifact.content); setComment(''); setError('')
  }
  const edit = () => selected && run(() => request(`/artifacts/${selected.id}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content: draft, user_id: 'demo-analyst' }),
  }).then(() => setComment('')), 'Revision saved as a draft.')
  const review = (status: 'approved' | 'rejected') => selected && run(() => request(`/artifacts/${selected.id}/status`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, user_id: 'demo-reviewer', comment: comment.trim() || (status === 'approved' ? 'Evidence verified.' : '') }),
  }).then(() => setComment('')), status === 'approved' ? 'Artifact approved and export unlocked.' : 'Artifact returned with reviewer guidance.')
  const exportJson = () => selected && run(async () => {
    const result = await request<{ payload: unknown }>(`/artifacts/${selected.id}/export`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target: 'jira', user_id: 'demo-reviewer' }),
    })
    const url = URL.createObjectURL(new Blob([JSON.stringify(result.payload, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `${selected.type}-${selected.id}.json`
    document.body.append(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }, 'Jira-compatible export created and audited.')

  const counts = (status: string) => artifacts.filter((item) => item.status === status).length

  return <div className="shell">
    <aside>
      <div className="brand"><span>BA</span><div><strong>Tracework</strong><small>Evidence → delivery</small></div></div>
      <nav aria-label="Primary"><button onClick={() => document.getElementById('workspace')?.scrollIntoView({ behavior: 'smooth' })}>Review workspace</button><button onClick={() => document.getElementById('documents')?.scrollIntoView({ behavior: 'smooth' })}>Documents</button><button onClick={() => document.getElementById('audit')?.scrollIntoView({ behavior: 'smooth' })}>Audit trail</button></nav>
      <div className="aside-note"><b>Local grounded mode</b><p>No evidence leaves this machine. Exports are explicit.</p></div>
    </aside>
    <main>
      <header><div><p className="eyebrow">CHECKOUT DISCOVERY / REQUIREMENTS PACK</p><h1>Turn source material into defensible work.</h1></div><button className="primary" onClick={seed} disabled={busy}>Seed demo workspace</button></header>
      {error && <div className="banner error" role="alert">{error}</div>}
      <div className="banner" aria-live="polite">{notice}</div>
      <section className="stats" aria-label="Artifact counts">
        <article><span>Corpus</span><b>{documents.length}</b><small>{documents.length === 1 ? 'Source document indexed' : 'Source documents indexed'}</small></article>
        <article><span>In review</span><b>{counts('draft')}</b><small>Awaiting decision</small></article>
        <article><span>Approved</span><b>{counts('approved')}</b><small>Eligible to export</small></article>
        <article><span>Audit events</span><b>{audit.length}</b><small>Append-only actions</small></article>
      </section>
      <section className="workgrid" id="workspace">
        <div className="panel">
          <div className="panel-title"><div><p className="eyebrow">GENERATION STUDIO</p><h2>Source-backed artifacts</h2></div><span className="status">{busy ? 'Working…' : 'Ready'}</span></div>
          <form className="generate" onSubmit={generate}>
            <label>Evidence question<input value={query} onChange={(event) => setQuery(event.target.value)} minLength={3} required/></label>
            <label>Artifact type<select value={type} onChange={(event) => setType(event.target.value)}>
              <option value="user_story">User story</option><option value="acceptance_criteria">Acceptance criteria</option><option value="risk">Risk register</option><option value="assumption">Assumptions</option><option value="process_summary">Process summary</option><option value="implementation_ticket">Implementation ticket</option>
            </select></label>
            <button className="primary" disabled={busy}>Generate</button>
          </form>
          <form className="upload" id="documents" onSubmit={upload}><label>Index another source<input type="file" name="file" accept=".txt,.md,.html,.pdf,.docx" required /></label><button disabled={busy}>Upload</button></form>
          {documents.length > 0 && <ul className="doc-list" aria-label="Indexed sources">{documents.map((document) => <li key={document.id}><span>{document.filename}</span><small>{new Date(document.uploaded_at).toLocaleDateString()}</small></li>)}</ul>}
          <div className="artifact-list">
            {artifacts.length === 0 && <div className="empty">No artifacts yet. Seed the demo or upload evidence.</div>}
            {artifacts.map((artifact) => <button key={artifact.id} className={selected?.id === artifact.id ? 'artifact selected' : 'artifact'} aria-pressed={selected?.id === artifact.id} onClick={() => selectArtifact(artifact)}>
              <span className={`dot ${artifact.status}`}></span><div><b>{artifact.type.replaceAll('_', ' ')}</b><small>Revision {artifact.revision} · {artifact.citations.length} {artifact.citations.length === 1 ? 'citation' : 'citations'}</small></div><em>{artifact.status}</em>
            </button>)}
          </div>
        </div>
        <div className="panel review">
          <div className="panel-title"><div><p className="eyebrow">REVIEW DESK</p><h2>{selected ? selected.type.replaceAll('_', ' ') : 'Select an artifact'}</h2></div>{selected && <span className={`pill ${selected.status}`}>{selected.status}</span>}</div>
          {!selected ? <div className="empty tall">Choose an artifact to inspect its exact evidence and make a review decision.</div> : <>
            <label>Artifact content<textarea value={draft} onChange={(event) => setDraft(event.target.value)} rows={12} disabled={selected.status === 'exported'} /></label>
            <h3>Source evidence</h3>
            <div className="citations">{selected.citations.map((citation, index) => <blockquote key={citation.chunk_id}><span>{String(index + 1).padStart(2, '0')}</span>“{citation.quote}”<small>Chunk {citation.chunk_id.slice(0, 8)}</small></blockquote>)}</div>
            {selected.review_comment && <p className={`review-note ${selected.status}`}><b>{selected.status === 'rejected' ? 'Returned' : 'Reviewed'} by {selected.reviewer_id}:</b> {selected.review_comment}</p>}
            {['draft', 'rejected'].includes(selected.status) && <label>Reviewer comment<input value={comment} onChange={(event) => setComment(event.target.value)} maxLength={1000} placeholder="Required to reject; optional when approving" /></label>}
            {unsaved && <p className="hint" role="status">Unsaved edits. Save the revision before approving or rejecting, so the decision covers what you see.</p>}
            <div className="actions"><button onClick={edit} disabled={busy || selected.status === 'exported' || !unsaved || !draft.trim()}>Save revision</button><button className="danger" onClick={() => review('rejected')} disabled={busy || unsaved || selected.status !== 'draft' || !comment.trim()}>Reject</button><button className="primary" onClick={() => review('approved')} disabled={busy || unsaved || !['draft', 'rejected'].includes(selected.status)}>Approve</button><button onClick={exportJson} disabled={busy || selected.status !== 'approved'}>Export Jira JSON</button></div>
          </>}
        </div>
      </section>
      <section className="panel audit" id="audit"><div className="panel-title"><div><p className="eyebrow">ACCOUNTABILITY</p><h2>Recent audit events</h2></div></div><div className="timeline">{audit.slice(0, 6).map((item) => <div key={item.id}><span></span><b>{item.action.replaceAll('_', ' ')}</b><small>{item.user_id} · {new Date(item.timestamp).toLocaleString()}</small></div>)}</div></section>
    </main>
  </div>
}

export default App
