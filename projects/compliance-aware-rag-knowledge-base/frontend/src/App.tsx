import { type FormEvent, useEffect, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

const API_BASE = apiBase(import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8016/api')
type Tab = 'ask' | 'documents' | 'governance' | 'audit' | 'evaluation'
type Identity = { userId: string; role: string; teams: string; clearance: string }
type Citation = { document_id: string; document_title: string; quote: string; start_char: number; end_char: number; lexical_score: number; vector_score: number; relevance_score: number }
type Answer = { id: string; text: string; citations: Citation[]; confidence_score: number; low_confidence: boolean; abstained: boolean; model: string; prompt_version: string }
type DocumentItem = { id: string; title: string; filename: string; file_type: string; owner: string; team: string; sensitivity: string; allowed_roles: string[]; allowed_teams: string[]; status: string; version: number; chunk_count: number; created_at: string; expires_at: string; tags: string[] }
type AuditEvent = { id: string; event_type: string; actor_id?: string; timestamp: string; request_id?: string; details: Record<string, unknown> }
type RedactionRule = { id: string; name: string; pattern: string; replacement: string; enabled: boolean; version: number }
type Evaluation = { id: string; created_at: string; question_count: number; retrieval_hit_rate: number; citation_validity_rate: number; abstention_accuracy: number; permission_leak_count: number; average_latency_ms: number; overall_status: string }

const adminIdentity: Identity = { userId: 'demo-admin', role: 'admin', teams: 'security,product,general', clearance: 'restricted' }
const identityHeaders = (identity: Identity) => ({ 'X-User-ID': identity.userId, 'X-User-Role': identity.role, 'X-User-Teams': identity.teams, 'X-User-Clearance': identity.clearance })

async function api<T>(path: string, init?: RequestInit, identity?: Identity): Promise<T> {
  const isForm = init?.body instanceof FormData
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers: { ...(isForm ? {} : { 'Content-Type': 'application/json' }), ...(identity ? identityHeaders(identity) : {}), ...init?.headers } })
  if (!response.ok) { const payload = await response.json().catch(() => ({})); throw new Error(errorMessage(payload.detail, response.status)) }
  return response.json() as Promise<T>
}

function App() {
  const [tab, setTab] = useState<Tab>('ask')
  const [identity, setIdentity] = useState<Identity>({ userId: 'maya.employee', role: 'employee', teams: 'product,general', clearance: 'internal' })
  const [question, setQuestion] = useState('When does Project Atlas launch and who owns it?')
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [feedbackSent, setFeedbackSent] = useState(false)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [audit, setAudit] = useState<AuditEvent[]>([])
  const [redactions, setRedactions] = useState<RedactionRule[]>([])
  const [evaluations, setEvaluations] = useState<Evaluation[]>([])
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const loadAdminData = async () => {
    setLoading(true)
    try {
      const [docs, events, rules, runs] = await Promise.all([
        api<DocumentItem[]>('/admin/documents', undefined, adminIdentity),
        api<AuditEvent[]>('/admin/audit?limit=100', undefined, adminIdentity),
        api<RedactionRule[]>('/admin/redactions', undefined, adminIdentity),
        api<Evaluation[]>('/admin/evaluations', undefined, adminIdentity),
      ])
      setDocuments(docs); setAudit(events); setRedactions(rules); setEvaluations(runs)
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to load governance data') }
    finally { setLoading(false) }
  }

  useEffect(() => { void loadAdminData() }, [])

  const seed = async () => {
    setWorking(true); setError('')
    try { const result = await api<{ created_count: number }>('/demo/seed', { method: 'POST' }, adminIdentity); await loadAdminData(); setNotice(`${result.created_count} governed demo documents added.`) }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to seed knowledge base') }
    finally { setWorking(false) }
  }

  const ask = async (event: FormEvent) => {
    event.preventDefault(); setWorking(true); setError(''); setAnswer(null); setFeedbackSent(false)
    try { setAnswer(await api<Answer>('/query', { method: 'POST', body: JSON.stringify({ text: question, top_k: 5 }) }, identity)); await loadAdminData() }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to answer') }
    finally { setWorking(false) }
  }

  const sendFeedback = async (rating: number) => {
    if (!answer || feedbackSent) return
    setFeedbackSent(true)
    try { await api(`/answers/${answer.id}/feedback`, { method: 'POST', body: JSON.stringify({ rating, reason: rating >= 4 ? 'Useful and well cited' : 'Needs better evidence' }) }, identity); setNotice('Feedback linked to this answer and its audit trail.') }
    catch (err) { setFeedbackSent(false); setError(err instanceof Error ? err.message : 'Unable to save feedback') }
  }

  const upload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const formElement = event.currentTarget; const form = new FormData(formElement); setWorking(true); setError('')
    try { await api('/ingest', { method: 'POST', body: form }, adminIdentity); formElement.reset(); await loadAdminData(); setNotice('Document parsed, classified, chunked, indexed, and audited.') }
    catch (err) { setError(err instanceof Error ? err.message : 'Upload failed') }
    finally { setWorking(false) }
  }

  const toggleDocument = async (document: DocumentItem) => {
    setWorking(true)
    try { await api(`/admin/documents/${document.id}${document.status === 'deleted' ? '/restore' : ''}`, { method: document.status === 'deleted' ? 'POST' : 'DELETE' }, adminIdentity); await loadAdminData(); setNotice(`${document.title} ${document.status === 'deleted' ? 'restored' : 'soft deleted'}.`) }
    catch (err) { setError(err instanceof Error ? err.message : 'Document update failed') }
    finally { setWorking(false) }
  }

  const addRedaction = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const formElement = event.currentTarget; const form = new FormData(formElement); const payload = { name: String(form.get('name')), pattern: String(form.get('pattern')), replacement: '[REDACTED]', enabled: true, apply_to_ingestion: true, apply_to_audit: true }; setWorking(true); setError('')
    try { await api('/admin/redactions', { method: 'POST', body: JSON.stringify(payload) }, adminIdentity); formElement.reset(); await loadAdminData(); setNotice('Redaction rule validated, versioned, and enabled.') }
    catch (err) { setError(err instanceof Error ? err.message : 'Redaction rule rejected') }
    finally { setWorking(false) }
  }

  const runEvaluation = async () => {
    const golden = [
      { question: 'When does Project Atlas launch?', role: 'employee', teams: ['product'], clearance: 'internal', expected_keywords: ['Q3 2026'], should_abstain: false },
      { question: 'When is the emergency credential rotation?', role: 'contractor', teams: ['general'], clearance: 'internal', expected_keywords: [], should_abstain: true },
      { question: 'What is required for contractor repository access?', role: 'contractor', teams: ['general'], clearance: 'internal', expected_keywords: ['sponsor approval', 'security training'], should_abstain: false },
    ]
    setWorking(true); setError('')
    try { const run = await api<Evaluation>('/admin/evaluations', { method: 'POST', body: JSON.stringify(golden) }, adminIdentity); setEvaluations((current) => [run, ...current]); setNotice(`Evaluation ${run.overall_status}: ${run.question_count} golden questions completed.`); await loadAdminData() }
    catch (err) { setError(err instanceof Error ? err.message : 'Evaluation failed') }
    finally { setWorking(false) }
  }

  // An answer is only valid for the identity that asked; clear it when the claims change.
  const changeIdentity = (next: Identity) => { setIdentity(next); setAnswer(null); setFeedbackSent(false) }
  const activeDocuments = documents.filter((item) => item.status === 'active')
  const navItems: { key: Tab; label: string; icon: string }[] = [
    { key: 'ask', label: 'Ask', icon: '⌁' }, { key: 'documents', label: 'Documents', icon: '▱' }, { key: 'governance', label: 'Governance', icon: '◇' }, { key: 'audit', label: 'Audit trail', icon: '≡' }, { key: 'evaluation', label: 'Evaluation', icon: '◎' },
  ]

  return <div className="rag-app">
    <aside><div className="product-mark"><span>V</span><div><strong>Vaultline</strong><small>Governed knowledge</small></div></div><nav>{navItems.map((item) => <button aria-label={item.label} aria-current={tab === item.key ? 'page' : undefined} key={item.key} className={tab === item.key ? 'active' : ''} onClick={() => setTab(item.key)}><i>{item.icon}</i>{item.label}{item.key === 'documents' && <b>{activeDocuments.length}</b>}</button>)}</nav><div className="guard"><span>Policy boundary active</span><small>Demo header identity · not production SSO</small></div></aside>
    <section className="page"><header><div><span className="status-dot" />Policy engine online</div><div className="header-right"><button className="seed" onClick={seed} disabled={working}>Load governed demo</button><span className="identity-chip">{identity.role} · {identity.clearance}</span><span className="avatar">{identity.userId.slice(0, 2).toUpperCase()}</span></div></header>
      <main>
        {error && <div className="banner error" role="alert"><b>Request stopped</b><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}>×</button></div>}
        {notice && <div className="banner success" role="status"><b>Recorded</b><span>{notice}</span><button aria-label="Dismiss message" onClick={() => setNotice('')}>×</button></div>}
        {tab === 'ask' && <>
          <section className="hero"><span className="overline">Evidence before eloquence</span><h1>Ask your knowledge base.<br/><em>See why you can trust it.</em></h1><p>Access is filtered before retrieval. Answers quote only permitted source text—or abstain.</p></section>
          <section className="identity-bar"><div><span>Demo identity context</span><small>This simulates claims supplied by an upstream identity provider.</small></div><label>Role<select value={identity.role} onChange={(e) => changeIdentity({ ...identity, role: e.target.value })}><option>employee</option><option>contractor</option><option>admin</option></select></label><label>Teams<input value={identity.teams} onChange={(e) => changeIdentity({ ...identity, teams: e.target.value })} /></label><label>Clearance<select value={identity.clearance} onChange={(e) => changeIdentity({ ...identity, clearance: e.target.value })}><option>public</option><option>internal</option><option>confidential</option><option>restricted</option></select></label></section>
          <form className="ask-box" onSubmit={ask}><textarea value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={(event) => { if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && !working && question.trim().length >= 2) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} minLength={2} maxLength={2000} aria-label="Question" placeholder="Ask a question grounded in your documents…"/><div><span>Ctrl / ⌘ Enter to ask · {activeDocuments.length} active documents</span><button disabled={working || question.trim().length < 2}>{working ? 'Applying policy…' : 'Ask with evidence'} <i>→</i></button></div></form>
          {!answer && !working && activeDocuments.length === 0 && <div className="empty-inline"><span>▱</span><div><strong>No active knowledge yet</strong><small>Load the governed demo or upload a document from the Documents view.</small></div><button onClick={seed}>Load demo</button></div>}
          {working && <div className="thinking"><span className="loader"/><div><strong>Applying access policy before retrieval</strong><small>status · expiry · role · team · clearance</small></div></div>}
          {answer && <section className={`answer ${answer.abstained ? 'abstained' : ''}`}><div className="answer-head"><div><span className="answer-icon">{answer.abstained ? '!' : '✓'}</span><div><strong>{answer.abstained ? 'Safely abstained' : 'Grounded answer'}</strong><small>{answer.model} · {Math.round(answer.confidence_score * 100)}% retrieval confidence</small></div></div><span className={answer.low_confidence ? 'confidence low' : 'confidence'}>{answer.low_confidence ? 'Low confidence' : 'Supported'}</span></div><div className="answer-text">{answer.text.split('\n').map((line, index) => line && <p key={index}>{line}</p>)}</div>{answer.citations.length > 0 && <div className="citations"><h3>Sources used</h3>{answer.citations.map((citation, index) => <details key={citation.document_id + index}><summary><span>{index + 1}</span><b>{citation.document_title}</b><em>{Math.round(citation.relevance_score * 100)}% match</em></summary><blockquote>“{citation.quote}”</blockquote><small>characters {citation.start_char}–{citation.end_char} · lexical {citation.lexical_score.toFixed(2)} · vector {citation.vector_score.toFixed(2)}</small></details>)}</div>}<div className="answer-footer"><span>{feedbackSent ? 'Thanks. Feedback recorded for this answer.' : 'Was this grounded answer useful?'}</span><button onClick={() => sendFeedback(5)} disabled={feedbackSent}>Yes</button><button onClick={() => sendFeedback(2)} disabled={feedbackSent}>Not quite</button><code>{answer.prompt_version}</code></div></section>}
        </>}

        {tab === 'documents' && <><section className="section-title"><div><span className="overline">Controlled corpus</span><h1>Document library</h1><p>Classification, permissions, lifecycle, parser evidence, and retention in one view.</p></div></section><section className="two-column"><article className="card upload-card"><h2>Ingest a document</h2><p>PDF, DOCX, Markdown, HTML, or UTF-8 text · max 5 MiB</p><form onSubmit={upload}><label>File<input type="file" name="file" required accept=".pdf,.docx,.md,.html,.htm,.txt" /></label><label>Title<input name="title" required placeholder="Policy handbook" /></label><div className="form-row"><label>Allowed roles<input name="allowed_roles" defaultValue="employee, admin" /></label><label>Allowed teams<input name="allowed_teams" defaultValue="general" /></label></div><div className="form-row"><label>Owner<input name="owner" defaultValue="knowledge-admin" /></label><label>Team<input name="team" defaultValue="general" /></label></div><div className="form-row"><label>Sensitivity<select name="sensitivity" defaultValue="internal"><option>public</option><option>internal</option><option>confidential</option><option>restricted</option></select></label><label>Retention days<input type="number" name="retention_days" min="1" max="3650" defaultValue="365" /></label></div><input type="hidden" name="source" value="console-upload"/><button className="primary" disabled={working}>Parse, classify & index</button></form></article><article className="card library"><div className="card-head"><h2>Governed documents</h2><span>{activeDocuments.length} active / {documents.length} total</span></div>{loading ? <div className="loader"/> : documents.length === 0 ? <div className="mini-empty">No documents ingested.</div> : documents.map((document) => <div className={`doc-row ${document.status}`} key={document.id}><span className="file-icon">{document.filename.split('.').pop()?.toUpperCase()}</span><div><strong>{document.title}</strong><small>{document.owner} · {document.team} · v{document.version} · {document.chunk_count} chunks</small><span><i className={document.sensitivity}>{document.sensitivity}</i>{document.allowed_roles.map((role) => <i key={role}>{role}</i>)}</span></div><div><small>Expires {new Date(document.expires_at).toLocaleDateString()}</small><button disabled={working} onClick={() => toggleDocument(document)}>{document.status === 'deleted' ? 'Restore' : 'Soft delete'}</button></div></div>)}</article></section></>}

        {tab === 'governance' && <><section className="section-title"><div><span className="overline">Policy controls</span><h1>Governance workspace</h1><p>Versioned redaction, lifecycle boundaries, and transparent policy posture.</p></div></section><section className="governance-grid"><article className="card"><h2>Create redaction rule</h2><p>Rules apply during ingestion and to audit-safe text. Nested repetition is rejected.</p><form onSubmit={addRedaction}><label>Name<input name="name" required placeholder="Email addresses" /></label><label>Regular expression<input name="pattern" required defaultValue="[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}" /></label><button className="primary" disabled={working}>Validate & enable</button></form></article><article className="card"><div className="card-head"><h2>Enabled redactions</h2><span>{redactions.length} rules</span></div>{redactions.length === 0 ? <div className="mini-empty">No redaction rules configured.</div> : redactions.map((rule) => <div className="policy-row" key={rule.id}><span>⌁</span><div><strong>{rule.name}</strong><code>{rule.pattern}</code><small>v{rule.version} · {rule.enabled ? 'enabled' : 'disabled'}</small></div></div>)}</article><article className="card policy-posture"><h2>Policy sequence</h2>{['Document status & retention', 'Sensitivity clearance', 'Role membership', 'Team intersection', 'Hybrid relevance threshold', 'Grounded citation validation'].map((step, index) => <div key={step}><span>{index + 1}</span><strong>{step}</strong><i>enforced</i></div>)}</article></section></>}

        {tab === 'audit' && <><section className="section-title"><div><span className="overline">Reconstruct every decision</span><h1>Audit trail</h1><p>Actors, policy counts, retrieved evidence, answer versions, feedback, and timing.</p></div></section><article className="card audit-card"><div className="audit-head"><span>Time</span><span>Event</span><span>Actor</span><span>Evidence summary</span></div>{audit.length === 0 ? <div className="mini-empty">No audit events yet.</div> : audit.map((event) => <details className="audit-row" key={event.id}><summary><span>{new Date(event.timestamp).toLocaleString()}</span><span><i>{event.event_type.replaceAll('_', ' ')}</i></span><span>{event.actor_id ?? 'system'}</span><span>{Object.keys(event.details).slice(0, 4).join(' · ')}</span></summary><pre>{JSON.stringify(event.details, null, 2)}</pre></details>)}</article></>}

        {tab === 'evaluation' && <><section className="section-title action-title"><div><span className="overline">Regression evidence</span><h1>Golden-set evaluation</h1><p>Retrieval hits, valid citations, abstention, latency, and permission leakage.</p></div><button className="primary" onClick={runEvaluation} disabled={working || !activeDocuments.length}>{working ? 'Running cases…' : 'Run 3-case golden set'}</button></section>{evaluations.length === 0 ? <div className="empty-eval"><span>◎</span><h2>No evaluation evidence yet</h2><p>Load the demo corpus, then test authorized retrieval, protected abstention, and contractor access.</p></div> : <><section className="eval-metrics"><article><span>Overall</span><strong className={evaluations[0].overall_status.toLowerCase()}>{evaluations[0].overall_status}</strong></article><article><span>Retrieval hits</span><strong>{Math.round(evaluations[0].retrieval_hit_rate * 100)}%</strong></article><article><span>Citation validity</span><strong>{Math.round(evaluations[0].citation_validity_rate * 100)}%</strong></article><article><span>Abstention accuracy</span><strong>{Math.round(evaluations[0].abstention_accuracy * 100)}%</strong></article><article><span>Permission leaks</span><strong className={evaluations[0].permission_leak_count ? 'fail' : 'pass'}>{evaluations[0].permission_leak_count}</strong></article></section><article className="card eval-history"><div className="card-head"><h2>Evaluation history</h2><span>Newest first</span></div>{evaluations.map((run) => <div key={run.id}><i className={run.overall_status.toLowerCase()}>{run.overall_status}</i><span><strong>{run.question_count} golden questions</strong><small>{new Date(run.created_at).toLocaleString()} · {run.average_latency_ms.toFixed(1)} ms average</small></span><span>{Math.round(run.retrieval_hit_rate * 100)}% hit · {run.permission_leak_count} leaks</span></div>)}</article></> }</>}
      </main>
    </section>
  </div>
}

export default App
