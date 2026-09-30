import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

const API_BASE = apiBase(import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8015/api')

type ColumnProfile = { name: string; dtype: string; null_count: number; null_ratio: number; unique_count: number; uniqueness_ratio: number; minimum?: number; maximum?: number }
type Profile = { id: string; timestamp: string; row_count: number; duplicate_row_count: number; is_baseline: boolean; columns: ColumnProfile[] }
type Source = { id: string; name: string; type: string; owner: string; enabled: boolean; description: string }
type Dataset = { source: Source; latest_profile: Profile | null; health_score: number | null; health_status: string; active_issue_count: number; rule_count: number }
type Rule = { id: string; rule_type: string; severity: string; enabled: boolean; parameters: Record<string, unknown> }
type DriftSignal = { drift_type: string; column?: string; details: string; score: number; threshold: number }
type Report = { health_score: number; health_status: string; profile: Profile; rule_results: { rule_id: string; passed: boolean; severity: string; details: string }[]; drift_result: { has_drift: boolean; details: string; signals: DriftSignal[] }; issues_created: Issue[]; issues_updated: Issue[] }
type Issue = { id: string; source_id: string; title: string; description: string; status: string; severity: string; owner?: string; occurrence_count: number; suggested_remediation: string; updated_at: string }

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(errorMessage(payload.detail, response.status))
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function HealthRing({ score }: { score: number }) {
  const color = score >= 90 ? '#18a779' : score >= 70 ? '#d79524' : '#df5f63'
  return <span className="health-ring" role="img" aria-label={`Health score ${score.toFixed(0)} of 100`} style={{ background: `conic-gradient(${color} ${score}%, #e5e9e7 0)` }}><i>{score.toFixed(0)}</i></span>
}

// Same-day evidence shows the time; older evidence also shows the date so stale snapshots are obvious.
function formatObserved(timestamp: string) {
  const date = new Date(timestamp)
  const time = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  return date.toDateString() === new Date().toDateString() ? `Today ${time}` : `${date.toLocaleDateString([], { day: 'numeric', month: 'short' })}, ${time}`
}

function App() {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [issues, setIssues] = useState<Issue[]>([])
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [rules, setRules] = useState<Rule[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const selected = useMemo(() => datasets.find((dataset) => dataset.source.id === selectedId), [datasets, selectedId])
  const activeIssues = issues.filter((issue) => issue.status !== 'resolved')
  const observed = datasets.filter((item) => item.health_score !== null)
  // Null until at least one dataset has been observed, so an empty portfolio never reads as "0 · At risk".
  const avgHealth = observed.length ? observed.reduce((sum, item) => sum + (item.health_score ?? 0), 0) / observed.length : null

  const refresh = async (preferredId?: string) => {
    setLoading(true)
    setError('')
    try {
      const [nextDatasets, nextIssues] = await Promise.all([api<Dataset[]>('/datasets'), api<Issue[]>('/issues')])
      setDatasets(nextDatasets)
      setIssues(nextIssues)
      const id = preferredId || selectedId || nextDatasets[0]?.source.id || ''
      setSelectedId(id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load observatory')
    } finally { setLoading(false) }
  }

  // Initial catalog hydration is mount-only; workflow actions refresh explicitly.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void refresh() }, [])

  useEffect(() => {
    if (!selectedId) { setProfiles([]); setRules([]); return }
    Promise.all([api<Profile[]>(`/sources/${selectedId}/profiles`), api<Rule[]>(`/sources/${selectedId}/rules`)])
      .then(([nextProfiles, nextRules]) => { setProfiles(nextProfiles); setRules(nextRules) })
      .catch((err) => setError(err instanceof Error ? err.message : 'Unable to load dataset evidence'))
  }, [selectedId, datasets])

  const seed = async () => {
    setWorking(true); setError('')
    try { await api('/demo/seed?reset=true', { method: 'POST' }); setReport(null); await refresh('orders_daily'); setNotice('Two healthy datasets, baselines, and six rules are ready.') }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to seed demo') }
    finally { setWorking(false) }
  }

  const observe = async () => {
    if (!selectedId) return
    setWorking(true); setError('')
    try { const next = await api<Report>(`/observe/${selectedId}`, { method: 'POST' }); setReport(next); await refresh(selectedId); setNotice(`Observation completed at ${next.health_score.toFixed(0)} health.`) }
    catch (err) { setError(err instanceof Error ? err.message : 'Observation failed') }
    finally { setWorking(false) }
  }

  const simulateDrift = async () => {
    setWorking(true); setError('')
    try { await api('/demo/drift', { method: 'POST' }); setSelectedId('orders_daily'); const next = await api<Report>('/observe/orders_daily', { method: 'POST' }); setReport(next); await refresh('orders_daily'); setNotice(`${next.drift_result.signals.length} drift signals captured with incident evidence.`) }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to introduce demo drift') }
    finally { setWorking(false) }
  }

  const resolveIssue = async (issue: Issue) => {
    setWorking(true); setError('')
    try { await api(`/issues/${issue.id}`, { method: 'PATCH', body: JSON.stringify({ status: 'resolved', actor: 'demo-operator', comment: 'Reviewed and resolved from the observatory console.' }) }); await refresh(selectedId); setNotice(`Resolved “${issue.title}”.`) }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to resolve issue') }
    finally { setWorking(false) }
  }

  return <div className="observatory">
    <aside>
      <div className="logo"><span>O</span><div><strong>Orbit</strong><small>Data observatory</small></div></div>
      <nav><a className="active" href="#overview"><i>◫</i>Overview</a><a href="#datasets"><i>◇</i>Datasets</a><a href="#rules"><i>✓</i>Expectations</a><a href="#incidents"><i>!</i>Incidents{activeIssues.length > 0 && <b>{activeIssues.length}</b>}</a></nav>
      <div className="mode"><span className="live-dot" />Local evidence mode<small>External delivery disabled</small></div>
    </aside>
    <div className="content-shell">
      <header><div><span className="breadcrumb">Workspace / <b>Reliability</b></span></div><div className="header-actions"><button className="quiet" onClick={simulateDrift} disabled={working || !datasets.length}>Introduce demo drift</button><button className="primary" onClick={observe} disabled={working || !selectedId}>{working ? 'Running…' : 'Run observation'}</button><span className="avatar">DS</span></div></header>
      <main id="overview">
        <section className="title-row"><div><span className="overline">Data reliability command center</span><h1>Know what changed before your users do.</h1><p>Profiles, expectations, drift evidence, and incident ownership in one operational loop.</p></div><button className="seed-button" onClick={seed} disabled={working}>↻ Load clean demo</button></section>
        {error && <div className="banner error" role="alert"><b>Action failed</b><span>{error}</span><button onClick={() => setError('')}>×</button></div>}
        {notice && <div className="banner success" role="status"><b>Evidence updated</b><span>{notice}</span><button onClick={() => setNotice('')}>×</button></div>}
        {loading ? <div className="empty"><span className="loader" />Opening observatory…</div> : datasets.length === 0 ? <div className="empty"><span className="empty-glyph">◎</span><h2>Your observatory is quiet</h2><p>Load genuine inline/JSON sample data, versioned rules, and healthy baselines.</p><button className="primary" onClick={seed}>Load clean demo</button></div> : <>
          <section className="metrics">
            <article><span>Portfolio health</span><div><strong>{avgHealth === null ? '—' : avgHealth.toFixed(0)}</strong>{avgHealth === null ? <em>No observations yet</em> : <em className={avgHealth >= 90 ? 'good' : 'bad'}>{avgHealth >= 90 ? 'Trusted' : 'At risk'}</em>}</div><small>Average of latest observations</small></article>
            <article><span>Observed datasets</span><div><strong>{observed.length}</strong><em>{datasets.length} registered</em></div><small>{datasets.reduce((sum, item) => sum + (item.latest_profile?.row_count ?? 0), 0)} rows in latest snapshots</small></article>
            <article><span>Active incidents</span><div><strong className={activeIssues.length ? 'red' : ''}>{activeIssues.length}</strong><em>{issues.filter((item) => item.status === 'resolved').length} resolved</em></div><small>Deduplicated by failure fingerprint</small></article>
            <article><span>Expectation coverage</span><div><strong>{datasets.reduce((sum, item) => sum + item.rule_count, 0)}</strong><em>rules enabled</em></div><small>Schema, volume, freshness & business quality</small></article>
          </section>

          <section className="grid" id="datasets">
            <article className="card dataset-card">
              <div className="card-head"><div><span className="overline">Catalog</span><h2>Dataset health</h2></div><span className="subtle">Latest evidence</span></div>
              <div className="dataset-table"><div className="table-head"><span>Dataset</span><span>Freshness</span><span>Rows</span><span>Health</span></div>{datasets.map((dataset) => <button key={dataset.source.id} aria-pressed={selectedId === dataset.source.id} className={selectedId === dataset.source.id ? 'selected' : ''} onClick={() => { setSelectedId(dataset.source.id); setReport(null) }}><span><i className={`source-icon ${dataset.source.type}`}>{dataset.source.type === 'json' ? '{}' : '▦'}</i><span><strong>{dataset.source.name}</strong><small>{dataset.source.id} · {dataset.source.owner}</small></span></span><span title={dataset.latest_profile ? new Date(dataset.latest_profile.timestamp).toLocaleString() : undefined}>{dataset.latest_profile ? formatObserved(dataset.latest_profile.timestamp) : 'Never'}</span><span>{dataset.latest_profile?.row_count ?? '—'}</span><span className={`health-pill ${dataset.health_status}`}>{dataset.health_score?.toFixed(0) ?? 'New'} · {dataset.health_status.replace('_', ' ')}</span></button>)}</div>
            </article>

            <article className="card evidence-card">
              <div className="card-head"><div><span className="overline">Selected dataset</span><h2>{selected?.source.name}</h2></div>{selected?.health_score !== null && selected?.health_score !== undefined && <HealthRing score={selected.health_score} />}</div>
              {selected?.latest_profile ? <><div className="profile-summary"><span><small>Rows</small><strong>{selected.latest_profile.row_count}</strong></span><span><small>Columns</small><strong>{selected.latest_profile.columns.length}</strong></span><span><small>Duplicates</small><strong>{selected.latest_profile.duplicate_row_count}</strong></span><span><small>Snapshots</small><strong>{profiles.length}</strong></span></div><div className="columns"><div className="columns-head"><span>Column</span><span>Type</span><span>Null</span><span>Unique</span></div>{selected.latest_profile.columns.slice(0, 6).map((column) => <div key={column.name}><strong>{column.name}</strong><code>{column.dtype}</code><span>{(column.null_ratio * 100).toFixed(1)}%</span><span>{(column.uniqueness_ratio * 100).toFixed(0)}%</span></div>)}{selected.latest_profile.columns.length > 6 && <small className="more-columns">+{selected.latest_profile.columns.length - 6} more columns in the stored profile</small>}</div></> : <p className="subtle">Run the first observation to create an immutable profile.</p>}
            </article>
          </section>

          <section className="grid lower">
            <article className="card" id="rules"><div className="card-head"><div><span className="overline">Expectations</span><h2>Rule coverage</h2></div><b className="count">{rules.length}</b></div><div className="rule-list">{rules.map((rule) => { const result = report?.rule_results.find((item) => item.rule_id === rule.id); return <div key={rule.id}><span className={`rule-status ${result ? (result.passed ? 'pass' : 'fail') : ''}`}>{result ? (result.passed ? '✓' : '!') : '•'}</span><span><strong>{rule.id}</strong><small>{rule.rule_type.replace('_', ' ')} · {rule.severity}</small>{result && <em>{result.details}</em>}</span></div> })}</div>{report?.drift_result.has_drift && <div className="drift-box"><b>{report.drift_result.signals.length} drift signals</b>{report.drift_result.signals.slice(0, 3).map((signal) => <span key={`${signal.drift_type}-${signal.column}`}>{signal.drift_type} {signal.column && `· ${signal.column}`}: {signal.details}</span>)}</div>}</article>
            <article className="card" id="incidents"><div className="card-head"><div><span className="overline">Triage queue</span><h2>Active incidents</h2></div><span className="subtle">Newest evidence first</span></div><div className="incident-list">{activeIssues.length === 0 ? <div className="all-clear"><span>✓</span><strong>No active incidents</strong><small>Repeated failures are deduplicated automatically.</small></div> : activeIssues.slice(0, 5).map((issue) => <div className="incident" key={issue.id}><i className={issue.severity}>{issue.severity[0].toUpperCase()}</i><span><strong>{issue.title}</strong><small>{issue.source_id} · {issue.owner ?? 'Unassigned'} · seen {issue.occurrence_count}×</small><p>{issue.description}</p></span><button onClick={() => resolveIssue(issue)} disabled={working}>Resolve</button></div>)}</div></article>
          </section>
        </>}
      </main>
    </div>
  </div>
}

export default App
