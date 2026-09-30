import { useEffect, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

const API = apiBase(import.meta.env.VITE_API_URL ?? 'http://localhost:8009/api')
type Alert = { id: string; status: string; version: number; reviewed_by?: string; event: { id: string; user_id: string; type: string; amount: number; location: string; device_id: string; timestamp: string }; features: { velocity_1h: number; amount_sum_24h: number; distinct_locations_24h: number; distinct_devices_24h: number; failed_attempts_1h: number; amount_spike_ratio: number; geo_anomaly: boolean; device_changed: boolean }; score: { anomaly_score: number; rule_score: number; total_risk_score: number; reason_codes: string[]; contributions: Record<string, number>; model_version: string; policy_version: string } }
type Metrics = { total_events: number; total_alerts: number; pending_alerts: number; reviewed_alerts: number; true_positives: number; false_positives: number; false_positive_rate: number; precision: number; average_risk_score: number; drift_index?: number; reason_code_counts: Record<string, number> }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) throw new Error(errorMessage((await response.json().catch(() => null))?.detail, response.status))
  return response.json() as Promise<T>
}

const emptyMetrics: Metrics = { total_events: 0, total_alerts: 0, pending_alerts: 0, reviewed_alerts: 0, true_positives: 0, false_positives: 0, false_positive_rate: 0, precision: 0, average_risk_score: 0, reason_code_counts: {} }

function App() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [active, setActive] = useState<Alert | null>(null)
  const [metrics, setMetrics] = useState<Metrics>(emptyMetrics)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [offline, setOffline] = useState(false)

  const refresh = async () => {
    const [queue, dashboard] = await Promise.all([request<Alert[]>('/alerts'), request<Metrics>('/metrics')])
    setAlerts(queue); setMetrics(dashboard); setLastUpdate(new Date()); setOffline(false)
    setActive((current) => current ? queue.find((alert) => alert.id === current.id) ?? null : null)
  }
  // Open the first item once data arrives, so the detail panel is never an empty prompt.
  useEffect(() => { if (!active && alerts.length) setActive(alerts[0]) }, [alerts, active])
  // Polling failures are shown in the live indicator and clear themselves on the next
  // successful poll, instead of leaving a stale error banner behind.
  useEffect(() => {
    const poll = () => refresh().catch(() => setOffline(true))
    poll()
    const timer = window.setInterval(poll, 10000)
    return () => window.clearInterval(timer)
  }, [])

  const seed = async () => {
    setBusy(true); setError('')
    try { await request('/demo/seed', { method: 'POST' }); setActive(null); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to seed scenario') }
    finally { setBusy(false) }
  }

  const decide = async (feedback: 'true_positive' | 'false_positive' | 'needs_more_information') => {
    if (!active) return
    setBusy(true); setError('')
    try {
      const updated = await request<Alert>(`/alerts/${active.id}/feedback`, { method: 'POST', body: JSON.stringify({ feedback, actor: 'analyst-local', note: feedback === 'true_positive' ? 'Signals and customer context confirm suspicious activity' : feedback === 'false_positive' ? 'Expected customer behavior confirmed' : 'Escalated for additional customer context', expected_version: active.version }) })
      setActive(updated); await refresh()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Decision failed')
      // A conflict means someone else changed the alert; show its current state.
      await refresh().catch(() => setOffline(true))
    }
    finally { setBusy(false) }
  }

  const topReasons = Object.entries(metrics.reason_code_counts).sort((a, b) => b[1] - a[1])
  return (
    <main className="app-shell">
      <header className="topbar"><div className="brand"><span className="brand-mark">R</span><span>Riskstream</span></div><nav><a href="#queue">Alert queue</a><a href="#monitoring">Monitoring</a><a href={`${API}/feedback/export`}>Feedback export</a></nav><span className="synthetic">SYNTHETIC DATA</span></header>
      <section className="hero"><div><p className="eyebrow">REAL-TIME RISK OPERATIONS</p><h1>Signals with a reason.</h1><p>Reproducible rolling features, explainable scores, and analyst feedback with conflict-safe decisions.</p></div><div className={offline ? 'live offline' : 'live'} role="status"><span aria-hidden="true"></span><div><b>{offline ? 'Connection lost' : 'Polling live'}</b><small>{offline ? `Retrying every 10s${lastUpdate ? ` · last update ${lastUpdate.toLocaleTimeString()}` : ''}` : lastUpdate ? `Updated ${lastUpdate.toLocaleTimeString()}` : 'Connecting…'}</small></div></div></section>
      <section className="stats"><div><span>Events scored</span><strong>{metrics.total_events}</strong><small>{metrics.total_alerts} at or above the 0.5 alert threshold</small></div><div><span>Pending alerts</span><strong>{metrics.pending_alerts}</strong><small>Awaiting an analyst decision</small></div><div><span>Reviewed precision</span><strong>{metrics.reviewed_alerts ? `${Math.round(metrics.precision * 100)}%` : '—'}</strong><small>{metrics.reviewed_alerts ? `${metrics.true_positives} of ${metrics.reviewed_alerts} final reviews confirmed` : 'No final reviews yet'}</small></div><div><span>Score drift</span><strong>{metrics.drift_index == null ? 'Need data' : metrics.drift_index.toFixed(3)}</strong><small>{metrics.drift_index == null ? 'Needs 4+ scored events' : 'Mean risk shift, earlier vs later half of events'}</small></div></section>
      {error && <div className="notice" role="alert">{error}</div>}
      <section className="workspace" id="queue">
        <aside className="panel queue-panel"><div className="panel-heading"><div><p className="eyebrow">PRIORITIZED QUEUE</p><h2>Alerts</h2></div><button className="seed" onClick={seed} disabled={busy}>Seed known scenario</button></div><div className="queue-list">{alerts.length === 0 && <div className="empty"><p>No alerts in queue.</p><small>Seed a deterministic fraud scenario to exercise the workflow.</small></div>}{alerts.map((alert) => <button key={alert.id} className={active?.id === alert.id ? 'active' : ''} aria-pressed={active?.id === alert.id} onClick={() => setActive(alert)}><span className={alert.score.total_risk_score >= 0.7 ? 'risk-score' : 'risk-score moderate'} aria-label={`Risk ${Math.round(alert.score.total_risk_score * 100)} of 100`}>{Math.round(alert.score.total_risk_score * 100)}</span><span><b>{alert.event.user_id}</b><small>{alert.event.type} · {alert.event.location} · ${alert.event.amount.toLocaleString()}</small><em>{alert.score.reason_codes.slice(0, 2).join(' + ')}</em></span><span className={`decision ${alert.status}`}>{alert.status.replaceAll('_', ' ')}</span></button>)}</div></aside>
        <section className="panel detail-panel">{!active ? <div className="empty-state"><span>◎</span><h2>Select an alert</h2><p>Feature evidence and analyst actions will appear here.</p></div> : <><div className="panel-heading"><div><p className="eyebrow">CASE {active.id.slice(0, 8)}</p><h2>{active.event.user_id}</h2></div><span className={`decision ${active.status}`}>{active.status.replaceAll('_', ' ')}</span></div><div className="score-hero"><div className="score-ring"><strong>{Math.round(active.score.total_risk_score * 100)}</strong><span>risk</span></div><div><p>Combined explainable score</p><div className="score-bars"><span><i style={{ width: `${active.score.anomaly_score * 100}%` }}></i></span><small>Statistical {Math.round(active.score.anomaly_score * 100)}%</small><span><i style={{ width: `${active.score.rule_score * 100}%` }}></i></span><small>Rules {Math.round(active.score.rule_score * 100)}%</small></div><code>{active.score.model_version} · {active.score.policy_version}</code></div></div><div className="reason-list">{active.score.reason_codes.map((reason) => <span key={reason}>{reason.replaceAll('_', ' ')}</span>)}</div><div className="event-summary"><div><span>Amount</span><b>${active.event.amount.toLocaleString()}</b></div><div><span>Location</span><b>{active.event.location}</b></div><div><span>Device</span><b>{active.event.device_id}</b></div><div><span>Event time</span><b>{new Date(active.event.timestamp).toLocaleTimeString()}</b></div></div><h3>Feature snapshot</h3><div className="feature-grid"><div><span>1h velocity</span><b>{active.features.velocity_1h}</b></div><div><span>24h amount</span><b>${active.features.amount_sum_24h.toLocaleString()}</b></div><div><span>Amount spike</span><b>{active.features.amount_spike_ratio.toFixed(1)}×</b></div><div><span>Locations / devices</span><b>{active.features.distinct_locations_24h} / {active.features.distinct_devices_24h}</b></div></div><div className="decision-bar"><span><b>Analyst decision</b><small>Version {active.version}; final TP/FP decisions are immutable.</small></span>{active.status === 'pending' || active.status === 'needs_more_information' ? <div><button className="secondary" onClick={() => decide('needs_more_information')} disabled={busy || active.status === 'needs_more_information'}>Need context</button><button className="secondary" onClick={() => decide('false_positive')} disabled={busy}>False positive</button><button onClick={() => decide('true_positive')} disabled={busy}>Confirm fraud</button></div> : <b className="reviewed">Reviewed by {active.reviewed_by}</b>}</div></>}</section>
      </section>
      <section className="monitoring" id="monitoring"><div className="panel"><p className="eyebrow">FEEDBACK QUALITY</p><h2>Reviewed outcomes</h2><div className="outcome" role="img" aria-label={metrics.reviewed_alerts ? `${metrics.true_positives} of ${metrics.reviewed_alerts} final reviews were true positives` : 'No final reviews yet'}><div style={{ width: `${metrics.reviewed_alerts ? (metrics.true_positives / metrics.reviewed_alerts) * 100 : 0}%` }}></div></div><p><b>{metrics.true_positives}</b> true positive · <b>{metrics.false_positives}</b> false positive</p></div><div className="panel"><p className="eyebrow">REASON DISTRIBUTION</p><h2>Leading signals</h2>{topReasons.length === 0 ? <p className="empty">No reason codes yet.</p> : <div className="reason-table">{topReasons.map(([reason, count]) => <div key={reason}><span>{reason.replaceAll('_', ' ')}</span><b>{count}</b></div>)}</div>}</div></section>
    </main>
  )
}

export default App
