import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

const API = apiBase(import.meta.env.VITE_API_URL ?? 'http://localhost:8012/api')
type Transition = { source: string; target: string; frequency: number; case_coverage: number; avg_duration_seconds: number; median_duration_seconds: number; p95_duration_seconds: number }
type Variant = { id: string; activities_sequence: string[]; frequency: number; coverage: number }
type Recommendation = { title: string; description: string; expected_impact: string; evidence: string[]; priority: number }
type Report = { id: string; created_at: string; total_cases: number; total_events: number; variants: Variant[]; transitions: Transition[]; bottlenecks: Transition[]; rework_loops: string[]; sla_breaches: unknown[]; ai_summary: string; recommendations: Recommendation[]; data_quality: { rejected_rows: number; duplicate_events: number; single_event_cases: number; issues: string[] } }

// Synthetic demo log; the API's POST /api/demo/seed analyzes the same rows.
const demoCsv = `case_id,activity,timestamp,resource
ORD-1042,Order received,2026-06-01T08:00:00Z,portal
ORD-1042,Credit review,2026-06-01T08:06:00Z,credit-team
ORD-1042,Manual correction,2026-06-03T12:30:00Z,ops
ORD-1042,Credit review,2026-06-03T13:00:00Z,credit-team
ORD-1042,Fulfilled,2026-06-03T14:00:00Z,warehouse
ORD-1043,Order received,2026-06-01T09:00:00Z,portal
ORD-1043,Credit review,2026-06-01T09:10:00Z,credit-team
ORD-1043,Fulfilled,2026-06-01T10:00:00Z,warehouse
ORD-1044,Order received,2026-06-01T10:00:00Z,portal
ORD-1044,Fulfilled,2026-06-01T10:20:00Z,warehouse`

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options })
  if (!response.ok) throw new Error(errorMessage((await response.json().catch(() => null))?.detail, response.status))
  return response.json() as Promise<T>
}

function hours(seconds: number) { return seconds < 3600 ? `${Math.round(seconds / 60)}m` : `${(seconds / 3600).toFixed(1)}h` }

function App() {
  const [csv, setCsv] = useState(demoCsv)
  const [report, setReport] = useState<Report | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [tab, setTab] = useState<'map' | 'variants'>('map')
  useEffect(() => {
    // Show the most recent stored report (for example the seeded demo) on arrival.
    request<Report[]>('/reports').then((reports) => { if (reports[0]) setReport(reports[0]) }).catch((reason: Error) => setError(reason.message))
  }, [])
  async function exportMarkdown() {
    if (!report) return
    setError('')
    try {
      const { markdown } = await request<{ markdown: string }>(`/export/${report.id}?format=markdown`)
      const url = URL.createObjectURL(new Blob([markdown], { type: 'text/markdown' }))
      const anchor = document.createElement('a')
      anchor.href = url; anchor.download = `process-report-${report.id.slice(0, 8)}.md`; anchor.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (reason) { setError((reason as Error).message) }
  }
  async function analyze() {
    setBusy(true); setError('')
    try { setReport(await request<Report>('/import/csv', { method: 'POST', body: JSON.stringify({ content: csv, config: { sla_seconds: 86400, bottleneck_seconds: 86400, bottleneck_min_frequency: 1 } }) })) }
    catch (reason) { setError((reason as Error).message) } finally { setBusy(false) }
  }
  const maxFrequency = useMemo(() => Math.max(1, ...(report?.transitions.map((item) => item.frequency) ?? [1])), [report])

  return <div className="shell process">
    <header className="topbar"><div className="brand"><span className="brand-mark" aria-hidden="true">F</span><span>FlowLens</span></div><nav aria-label="Sections"><a href="#discovery" onClick={() => setTab('map')}>Discover</a><a href="#discovery" onClick={() => setTab('variants')}>Cases</a><a href="#automation">Automation</a></nav><span className="status"><i aria-hidden="true" /> deterministic engine</span></header>
    <main>
      <section className="intro"><div><p className="eyebrow">Process intelligence workspace</p><h1>Turn event noise into<br />operational evidence.</h1><p className="lede">Import a real log, discover what work actually does, and build an automation backlog whose claims point back to measured transitions.</p></div><button className="primary" onClick={analyze} disabled={busy}>{busy ? 'Discovering process…' : 'Analyze event log'}</button></section>
      {error && <div className="notice error" role="alert">{error}</div>}
      <section className="metrics">
        <article><span>Cases</span><strong>{report?.total_cases ?? '—'}</strong><small>{report?.total_events ?? 0} normalized events</small></article>
        <article><span>Variants</span><strong>{report?.variants.length ?? '—'}</strong><small>{report?.variants[0] ? `${Math.round(report.variants[0].coverage * 100)}% dominant path` : 'awaiting analysis'}</small></article>
        <article><span>SLA breaches</span><strong className="danger">{report?.sla_breaches.length ?? '—'}</strong><small>24 hour threshold</small></article>
        <article><span>Automation candidates</span><strong className="accent">{report?.recommendations.length ?? '—'}</strong><small>evidence-linked</small></article>
      </section>
      <div className="workspace process-workspace" id="discovery">
        <aside className="panel importer"><div className="panel-title"><div><span>Event log</span><small>RFC-4180 CSV · timezone required</small></div><span className="tag">demo data</span></div><textarea aria-label="Event log CSV" wrap="off" value={csv} onChange={(event) => setCsv(event.target.value)} rows={17} spellCheck={false} /><div className="quality"><span>Required</span><code>case_id · activity · timestamp</code></div>{report && <dl><div><dt>Rejected rows</dt><dd>{report.data_quality.rejected_rows}</dd></div><div><dt>Duplicates removed</dt><dd>{report.data_quality.duplicate_events}</dd></div><div><dt>Single-event cases</dt><dd>{report.data_quality.single_event_cases}</dd></div></dl>}{report && report.data_quality.issues.length > 0 && <div className="issues"><b>Rejected rows</b>{report.data_quality.issues.slice(0, 3).map((issue) => <code key={issue} title={issue}>{issue.replace(/\s+/g, ' ').replace(/ \[type=.*$/, '')}</code>)}{report.data_quality.issues.length > 3 && <small>+{report.data_quality.issues.length - 3} more in the report export</small>}</div>}</aside>
        <section className="panel lab">
          <div className="panel-title"><div><span>Discovered process</span><small>{report?.ai_summary ?? 'Analyze the event log to build the directly-follows graph.'}</small></div><div className="tabs" role="group" aria-label="Process view"><button aria-pressed={tab === 'map'} className={tab === 'map' ? 'active' : ''} onClick={() => setTab('map')}>Transitions</button><button aria-pressed={tab === 'variants'} className={tab === 'variants' ? 'active' : ''} onClick={() => setTab('variants')}>Variants</button></div></div>
          {tab === 'map' ? <div className="flow-list">{report?.transitions.map((transition) => <article className={report.bottlenecks.some((item) => item.source === transition.source && item.target === transition.target) ? 'flow bottleneck' : 'flow'} key={`${transition.source}-${transition.target}`}><div className="flow-name"><b>{transition.source}</b><span>→</span><b>{transition.target}</b></div><div className="bar"><i style={{ width: `${Math.max(12, transition.frequency / maxFrequency * 100)}%` }} /></div><dl><div><dt>Count</dt><dd>{transition.frequency}</dd></div><div><dt>Mean</dt><dd>{hours(transition.avg_duration_seconds)}</dd></div><div><dt>P95</dt><dd>{hours(transition.p95_duration_seconds)}</dd></div><div><dt>Cases</dt><dd>{Math.round(transition.case_coverage * 100)}%</dd></div></dl></article>)}{!report && <div className="empty">Your process graph will appear here with frequency and delay evidence.</div>}</div> : <div className="variant-list">{report?.variants.map((variant) => <article key={variant.id}><span>{variant.id}</span><div><b>{variant.activities_sequence.join(' → ')}</b><small>{variant.frequency} case(s) · {Math.round(variant.coverage * 100)}% coverage</small></div></article>)}{!report && <div className="empty">Variants (distinct activity sequences) appear here after analysis.</div>}</div>}
        </section>
      </div>
      <section className="results" id="automation"><div className="section-heading"><div><p className="eyebrow">Measured opportunities</p><h2>Automation backlog</h2></div>{report ? <div className="exports"><span>report {report.id.slice(0, 8)} · {new Date(report.created_at).toLocaleString()}</span><button onClick={exportMarkdown}>Export Markdown</button></div> : <span>No report yet</span>}</div><div className="recommendations">{report?.recommendations.map((item) => <article className="recommendation" key={item.title}><span className="rank">P{item.priority}</span><div><h3>{item.title}</h3><p>{item.description}</p><div className="evidence-chips">{item.evidence.map((evidence) => <code key={evidence}>{evidence}</code>)}</div><small>{item.expected_impact}</small></div></article>)}{!report && <div className="empty">Recommendations appear only after their supporting metrics are computed.</div>}</div></section>
    </main>
  </div>
}

export default App
