import { useEffect, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

const API = apiBase(import.meta.env.VITE_API_URL ?? 'http://localhost:8006/api')

type IncidentType = 'latency_spike' | 'dependency_failure' | 'high_error_rate' | 'queue_backlog'
type Action = { id: string; description: string; command: string; risk_level: string; status: string; policy_reason: string; execution_output?: string }
type Plan = { id: string; incident_id: string; revision: number; hypothesis: string; confidence: number; runbook: string; evidence: { kind: string; source: string; observation: string }[]; actions: Action[] }
type Report = { id: string; incident_id: string; summary: string; actions_taken: string[]; time_to_resolution_minutes: number }
type Incident = { id: string; type: IncidentType; service_name: string; severity: string; status: string; created_at: string; telemetry: { metrics: Record<string, number>; logs: string[]; traces: Record<string, unknown>[] } }

// Scenario metrics have different units; label and format each one instead of assuming an error rate.
function formatMetric(name: string, value: number): [string, string] {
  if (name.endsWith('_rate')) return [name.replaceAll('_', ' '), `${(value * 100).toFixed(1)}%`]
  if (name.endsWith('_ms')) return [name.slice(0, -3).replaceAll('_', ' '), `${value.toLocaleString()} ms`]
  if (name.endsWith('_seconds')) return [name.slice(0, -8).replaceAll('_', ' '), `${value.toLocaleString()} s`]
  if (name === 'deploy_revision') return ['deploy revision', `rev-${value}`]
  return [name.replaceAll('_', ' '), value.toLocaleString()]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) throw new Error(errorMessage((await response.json().catch(() => null))?.detail, response.status))
  return response.json() as Promise<T>
}

function App() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [selected, setSelected] = useState<Incident | null>(null)
  const [plan, setPlan] = useState<Plan | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [type, setType] = useState<IncidentType>('queue_backlog')
  const [serviceName, setServiceName] = useState('orders-worker')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const refresh = async () => {
    const next = await request<Incident[]>('/incidents')
    setIncidents(next)
    setSelected((current) => current ? next.find((incident) => incident.id === current.id) ?? null : null)
  }
  useEffect(() => { refresh().catch((reason: Error) => setError(reason.message)) }, [])

  // Open the first item once data arrives, so the detail panel is never an empty prompt.
  useEffect(() => { if (!selected && incidents.length) setSelected(incidents[0]) }, [incidents, selected])

  // Reopen the latest plan (and report, once resolved) whenever the selection changes,
  // so switching incidents never loses a decision in progress or forces a re-analysis.
  const selectedId = selected?.id
  const selectedStatus = selected?.status
  useEffect(() => {
    if (!selectedId) return
    let current = true
    Promise.all([
      request<Plan[]>(`/incidents/${selectedId}/plans`),
      selectedStatus === 'resolved' ? request<Report[]>(`/reports?incident_id=${selectedId}`) : Promise.resolve([]),
    ]).then(([plans, reports]) => {
      if (!current) return
      const latest = plans.at(-1) ?? null
      setPlan((shown) => shown?.incident_id === selectedId && (!latest || shown.revision >= latest.revision) ? shown : latest)
      setReport(reports.at(-1) ?? null)
    }).catch((reason: Error) => { if (current) setError(reason.message) })
    return () => { current = false }
  }, [selectedId, selectedStatus])

  const createIncident = async () => {
    setBusy(true); setError('')
    try {
      const incident = await request<Incident>('/incidents/generate', { method: 'POST', body: JSON.stringify({ type, service_name: serviceName }) })
      setSelected(incident); setPlan(null); setReport(null); await refresh()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to create incident') }
    finally { setBusy(false) }
  }

  const analyze = async () => {
    if (!selected) return
    setBusy(true); setError('')
    try { setPlan(await request<Plan>(`/incidents/${selected.id}/analyze`, { method: 'POST' })); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Analysis failed') }
    finally { setBusy(false) }
  }

  const decide = async (actionIndex: number, decision: 'approve' | 'reject') => {
    if (!plan) return
    setBusy(true); setError('')
    try {
      const updated = await request<Plan>(`/plans/${plan.id}/${decision}`, {
        method: 'POST',
        body: JSON.stringify({ action_index: actionIndex, actor: 'local-operator', reason: decision === 'approve' ? 'Evidence and runbook support this action' : 'Risk outweighs expected recovery benefit' }),
      })
      setPlan(updated); await refresh()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Decision failed') }
    finally { setBusy(false) }
  }

  const openCount = incidents.filter((incident) => incident.status !== 'resolved').length
  const sevOne = incidents.filter((incident) => incident.severity === 'sev1' && incident.status !== 'resolved').length

  return (
    <main className="app-shell">
      <header className="topbar"><div className="brand"><span className="brand-mark">OP</span><span>OpsPilot</span></div><div className="top-actions"><span className="live-dot">Local safe mode</span><span className="avatar">SO</span></div></header>
      <section className="hero-band">
        <div><p className="eyebrow">INCIDENT COMMAND</p><h1>Evidence before action.</h1><p>Correlate telemetry, review policy, and keep every human decision auditable.</p></div>
        <button className="secondary" onClick={() => refresh().catch((reason: Error) => setError(reason.message))}>Refresh queue</button>
      </section>
      <section className="stats" aria-label="Incident summary">
        <div><span>Open incidents</span><strong>{openCount}</strong></div><div><span>Open SEV-1</span><strong>{sevOne}</strong></div><div><span>Policy mode</span><strong>Fail closed</strong></div><div><span>Executor</span><strong>Local / safe</strong></div>
      </section>
      {error && <div className="notice error" role="alert">{error}</div>}
      <section className="workspace">
        <aside className="panel queue-panel">
          <div className="panel-heading"><div><p className="eyebrow">QUEUE</p><h2>Incidents</h2></div><span className="count">{incidents.length}</span></div>
          <div className="form-stack">
            <label>Scenario<select value={type} onChange={(event) => setType(event.target.value as IncidentType)}><option value="latency_spike">Latency spike</option><option value="dependency_failure">Dependency failure</option><option value="high_error_rate">High error rate</option><option value="queue_backlog">Queue backlog</option></select></label>
            <label>Service<input value={serviceName} onChange={(event) => setServiceName(event.target.value)} /></label>
            <button onClick={createIncident} disabled={busy}>Generate incident</button>
          </div>
          <div className="item-list">{incidents.length === 0 && <p className="empty">No incidents yet. Generate a repeatable scenario above.</p>}{incidents.map((incident) => <button key={incident.id} className={`list-item ${selected?.id === incident.id ? 'selected' : ''}`} aria-pressed={selected?.id === incident.id} onClick={() => { if (selected?.id !== incident.id) { setSelected(incident); setPlan(null); setReport(null) } }}><span><b>{incident.service_name}</b><small>{incident.type.replaceAll('_', ' ')}</small></span><span className={`badge ${incident.status}`}>{incident.status}</span></button>)}</div>
        </aside>
        <section className="panel detail-panel">
          {!selected ? <div className="empty-state"><span className="empty-icon">⌁</span><h2>Select an incident</h2><p>Telemetry, evidence, and approval controls will appear here.</p></div> : <>
            <div className="panel-heading"><div><p className="eyebrow">{selected.severity.toUpperCase()} · {selected.type.replaceAll('_', ' ')}</p><h2>{selected.service_name}</h2></div><span className={`badge ${selected.status}`}>{selected.status}</span></div>
            <div className="telemetry-grid">{Object.entries(selected.telemetry.metrics).map(([name, value]) => { const [label, shown] = formatMetric(name, value); return <div key={name}><span>{label}</span><strong>{shown}</strong></div> })}</div>
            <ul className="log-lines" aria-label="Log samples">{selected.telemetry.logs.map((line) => <li className="log-line" key={line}>{line}</li>)}</ul>
            {report && <div className="report-card"><div><p className="eyebrow">POST-INCIDENT REPORT</p><b>{report.summary}</b><small>{report.actions_taken.length ? `Executed: ${report.actions_taken.join(', ')}` : 'No command executed'} · resolved in {report.time_to_resolution_minutes.toFixed(1)} min</small></div><a className="download" href={`${API}/reports/${report.id}/export`} download>Download Markdown</a></div>}
            {!plan ? (selected.status === 'resolved' ? null : <button onClick={analyze} disabled={busy}>Analyze telemetry &amp; runbooks</button>) : <div className="plan">
              <div className="hypothesis"><span className="score">{Math.round(plan.confidence * 100)}%</span><div><p className="eyebrow">PRIMARY HYPOTHESIS</p><h3>{plan.hypothesis}</h3><small className="runbook">Plan revision {plan.revision} · runbook reference <code>{plan.runbook}</code></small></div></div>
              <div className="evidence-row">{plan.evidence.map((item) => <span key={`${item.kind}-${item.source}`} className="evidence-chip" title={item.observation}>{item.kind}: {item.source}</span>)}</div>
              <h3>Remediation review</h3>
              {plan.actions.map((action, index) => <article className="action-card" key={action.id}><div className="action-title"><div><b>{action.description}</b><code>{action.command}</code></div><span className={`badge ${action.risk_level}`}>{action.risk_level} risk</span></div><p>{action.policy_reason}</p>{action.execution_output && <div className="success-output">{action.execution_output}</div>}<div className="button-row"><span className={`badge ${action.status}`}>{action.status}</span>{action.status === 'pending' && <><button className="secondary" onClick={() => decide(index, 'reject')} disabled={busy}>Reject</button><button onClick={() => decide(index, 'approve')} disabled={busy}>Approve &amp; execute</button></>}</div></article>)}
            </div>}
          </>}
        </section>
      </section>
    </main>
  )
}

export default App
