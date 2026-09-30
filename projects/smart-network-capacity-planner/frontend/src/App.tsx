import { type FormEvent, useEffect, useMemo, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

const API_BASE = apiBase(import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8014/api')
// OpenAPI is served next to the API prefix, both standalone and under the portfolio hub.
const DOCS_URL = `${API_BASE.replace(/\/api$/, '')}/docs`
const shortDate = (value: string) => new Date(value).toLocaleDateString([], { day: 'numeric', month: 'short' })

type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

type LinkSummary = {
  link_id: string
  device_id: string
  latest_timestamp: string
  sample_count: number
  utilization_mbps: number
  capacity_mbps: number
  utilization_pct: number
  latency_ms: number
  packet_loss_pct: number
  device_health: string
  stale: boolean
  data_quality_warnings: string[]
}

type Overview = {
  generated_at: string
  link_count: number
  sample_count: number
  stale_link_count: number
  critical_link_count: number
  links: LinkSummary[]
}

type ForecastPoint = {
  timestamp: string
  predicted_mbps: number
  lower_bound_mbps: number
  upper_bound_mbps: number
}

type Recommendation = {
  id: string
  action: string
  description: string
  cost_estimate_usd: number
  priority: number
  impact: string
  selected: boolean
  selection_reason: string
}

type Forecast = {
  link_id: string
  capacity_mbps: number
  forecast_points: ForecastPoint[]
  diagnostics: {
    method: string
    sample_count: number
    horizon_days: number
    slope_mbps_per_day: number
    mean_absolute_error_mbps: number
    warnings: string[]
  }
  risk: {
    risk_level: RiskLevel
    saturation_probability_pct: number
    estimated_days_to_saturation: number | null
    current_headroom_pct: number
    reasons: string[]
  }
  recommendations: Recommendation[]
}

type Scenario = {
  id: string
  name: string
  traffic_growth_multiplier: number
  traffic_reduction_pct: number
  added_capacity_mbps: number
  baseline_risk_level?: RiskLevel
  risk_reduction_pct?: number
  headroom_delta_pct?: number
  forecast?: Forecast
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(errorMessage(payload.detail, response.status))
  }
  return response.json() as Promise<T>
}

function formatMbps(value: number) {
  return value >= 1000 ? `${(value / 1000).toFixed(1)} Gbps` : `${value.toFixed(0)} Mbps`
}

function ForecastChart({ forecast }: { forecast: Forecast }) {
  const width = 760
  const height = 230
  const padding = 18
  const values = forecast.forecast_points.flatMap((point) => [point.lower_bound_mbps, point.upper_bound_mbps])
  const maxValue = Math.max(forecast.capacity_mbps, ...values) * 1.08
  const toPoint = (value: number, index: number) => {
    const x = padding + (index / Math.max(forecast.forecast_points.length - 1, 1)) * (width - padding * 2)
    const y = height - padding - (value / maxValue) * (height - padding * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }
  const predicted = forecast.forecast_points.map((point, index) => toPoint(point.predicted_mbps, index)).join(' ')
  const upper = forecast.forecast_points.map((point, index) => toPoint(point.upper_bound_mbps, index)).join(' ')
  const lower = [...forecast.forecast_points]
    .reverse()
    .map((point, reverseIndex) => toPoint(point.lower_bound_mbps, forecast.forecast_points.length - reverseIndex - 1))
    .join(' ')
  const capacityY = height - padding - (forecast.capacity_mbps / maxValue) * (height - padding * 2)

  return (
    <div className="chart" role="img" aria-label={`${forecast.diagnostics.horizon_days}-day forecast for ${forecast.link_id}: predicted ${formatMbps(forecast.forecast_points[forecast.forecast_points.length - 1].predicted_mbps)} at the horizon against ${formatMbps(forecast.capacity_mbps)} capacity`}>
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id="confidence" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#67e8f9" stopOpacity=".28" />
            <stop offset="100%" stopColor="#67e8f9" stopOpacity=".03" />
          </linearGradient>
        </defs>
        <polygon points={`${upper} ${lower}`} fill="url(#confidence)" />
        <line x1={padding} x2={width - padding} y1={capacityY} y2={capacityY} className="capacity-line" />
        <polyline points={predicted} className="forecast-line" />
      </svg>
      <div className="chart-axis" aria-hidden="true"><span>{shortDate(forecast.forecast_points[0].timestamp)}</span><span>{shortDate(forecast.forecast_points[Math.floor((forecast.forecast_points.length - 1) / 2)].timestamp)}</span><span>{shortDate(forecast.forecast_points[forecast.forecast_points.length - 1].timestamp)}</span></div>
      <div className="chart-legend"><span><i className="legend forecast" />Forecast</span><span><i className="legend bound" />95% confidence</span><span><i className="legend capacity" />Capacity {formatMbps(forecast.capacity_mbps)}</span></div>
    </div>
  )
}

function App() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [selectedLink, setSelectedLink] = useState('')
  const [forecast, setForecast] = useState<Forecast | null>(null)
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  // Loading the selected link's plan is tracked apart from user actions so the two never reset each other.
  const [planLoading, setPlanLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const selectedSummary = useMemo(
    () => overview?.links.find((link) => link.link_id === selectedLink),
    [overview, selectedLink],
  )

  const loadOverview = async () => {
    setLoading(true)
    setError('')
    try {
      const next = await api<Overview>('/overview')
      setOverview(next)
      setSelectedLink((current) => next.links.some((link) => link.link_id === current) ? current : next.links[0]?.link_id ?? '')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load portfolio')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadOverview() }, [])

  useEffect(() => {
    if (!selectedLink) { setPlanLoading(false); return }
    // Ignore responses for a link that is no longer selected, and never show the previous link's plan under the new name.
    let current = true
    setForecast(null)
    setScenarios([])
    setPlanLoading(true)
    setError('')
    Promise.all([
      api<Forecast>(`/forecast/${encodeURIComponent(selectedLink)}?days=90`),
      api<Scenario[]>(`/what-if/${encodeURIComponent(selectedLink)}`),
    ])
      .then(([nextForecast, nextScenarios]) => {
        if (!current) return
        setForecast(nextForecast)
        setScenarios(nextScenarios)
      })
      .catch((err) => { if (current) setError(err instanceof Error ? err.message : 'Unable to load link plan') })
      .finally(() => { if (current) setPlanLoading(false) })
    return () => { current = false }
  }, [selectedLink])

  const seedDemo = async () => {
    setWorking(true)
    setError('')
    try {
      await api('/demo/seed?reset=true', { method: 'POST' })
      setSelectedLink('')
      await loadOverview()
      setNotice('Demo portfolio loaded with 90 telemetry samples.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to seed demo')
    } finally {
      setWorking(false)
    }
  }

  const runScenario = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!selectedLink) return
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const payload = {
      name: String(form.get('name')),
      traffic_growth_multiplier: Number(form.get('growth')),
      traffic_reduction_pct: Number(form.get('reduction')),
      added_capacity_mbps: Number(form.get('capacity')),
      budget_usd: Number(form.get('budget')) || null,
      forecast_days: 90,
    }
    setWorking(true)
    setError('')
    try {
      const scenario = await api<Scenario>(`/what-if/${encodeURIComponent(selectedLink)}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setScenarios((current) => [...current, scenario])
      setNotice(`Scenario “${scenario.name}” saved and compared.`)
      formElement.reset()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to run scenario')
    } finally {
      setWorking(false)
    }
  }

  const exportReport = async () => {
    try {
      const response = await fetch(`${API_BASE}/reports/weekly?format=markdown`)
      if (!response.ok) throw new Error(`Report generation failed (${response.status})`)
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'weekly-capacity-report.md'
      anchor.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to export report')
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">CP</span><div><strong>Capacity Pilot</strong><small>Network planning workspace</small></div></div>
        <nav aria-label="Primary navigation"><a className="active" href="#portfolio">Portfolio</a><a href="#forecast">Forecast</a><a href="#scenarios">Scenarios</a></nav>
        <button className="button secondary" onClick={exportReport} disabled={!overview?.link_count}>Export weekly report</button>
      </header>

      <main>
        <section className="page-heading" id="portfolio">
          <div><span className="eyebrow">Planning cycle · live local workspace</span><h1>Capacity decisions, with the assumptions visible.</h1><p>Forecast saturation, compare interventions, and leave an auditable planning report.</p></div>
          <button className="button primary" onClick={seedDemo} disabled={working}>{working ? 'Working…' : 'Load demo portfolio'}</button>
        </section>

        {error && <div className="alert error" role="alert"><strong>Something needs attention.</strong><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}
        {notice && <div className="alert success" role="status"><strong>Updated.</strong><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss message">×</button></div>}

        {loading ? <div className="empty-state"><span className="spinner" />Loading capacity workspace…</div> : !overview?.link_count ? (
          <div className="empty-state"><span className="empty-icon">↗</span><h2>No telemetry yet</h2><p>Load the deterministic demo portfolio or POST a telemetry batch to <code>/api/telemetry</code>.</p><button className="button primary" onClick={seedDemo}>Load demo portfolio</button></div>
        ) : <>
          <section className="kpi-grid" aria-label="Portfolio summary">
            <article><span>Monitored links</span><strong>{overview.link_count}</strong><small>{overview.sample_count} retained samples</small></article>
            <article><span>High / critical</span><strong className={overview.critical_link_count ? 'warn-text' : ''}>{overview.critical_link_count}</strong><small>30-day confidence horizon</small></article>
            <article><span>Stale feeds</span><strong>{overview.stale_link_count}</strong><small>older than 48 hours</small></article>
            <article><span>Planning posture</span><strong className="posture">{overview.critical_link_count ? 'Act' : 'Observe'}</strong><small>based on current thresholds</small></article>
          </section>

          <section className="workspace-grid">
            <article className="panel link-panel">
              <div className="panel-title"><div><span className="eyebrow">Portfolio</span><h2>Link pressure</h2></div><span className="muted">Latest sample</span></div>
              <div className="link-list">
                {overview.links.map((link) => <button key={link.link_id} aria-pressed={selectedLink === link.link_id} className={`link-row ${selectedLink === link.link_id ? 'selected' : ''}`} onClick={() => setSelectedLink(link.link_id)}>
                  <span><strong>{link.link_id}</strong><small>{link.device_id} · {link.sample_count} samples</small></span>
                  <span className="util"><strong>{link.utilization_pct.toFixed(1)}%</strong><i><b style={{ width: `${Math.min(link.utilization_pct, 100)}%` }} /></i></span>
                </button>)}
              </div>
            </article>

            <article className="panel forecast-panel" id="forecast">
              <div className="panel-title"><div><span className="eyebrow">90-day outlook</span><h2>{selectedLink || 'Select a link'}</h2></div>{forecast && <span className={`risk ${forecast.risk.risk_level.toLowerCase()}`}>{forecast.risk.risk_level}</span>}</div>
              {planLoading && !forecast ? <div className="inline-loading"><span className="spinner" />Calculating forecast…</div> : forecast && <>
                <ForecastChart forecast={forecast} />
                <div className="forecast-stats"><span><small>Current load</small><strong>{selectedSummary ? formatMbps(selectedSummary.utilization_mbps) : '—'}</strong></span><span><small>Daily trend</small><strong>{forecast.diagnostics.slope_mbps_per_day > 0 ? '+' : ''}{forecast.diagnostics.slope_mbps_per_day.toFixed(1)} Mbps</strong></span><span><small>Headroom</small><strong>{forecast.risk.current_headroom_pct.toFixed(1)}%</strong></span><span><small>Threshold</small><strong>{forecast.risk.estimated_days_to_saturation ? `${forecast.risk.estimated_days_to_saturation} ${forecast.risk.estimated_days_to_saturation === 1 ? 'day' : 'days'}` : 'Beyond 90d'}</strong></span></div>
                <details><summary>Model evidence & assumptions</summary><p>{forecast.diagnostics.method} · {forecast.diagnostics.sample_count} samples · MAE {forecast.diagnostics.mean_absolute_error_mbps.toFixed(1)} Mbps</p>{forecast.risk.reasons.map((reason) => <p key={reason}>• {reason}</p>)}</details>
              </>}
            </article>
          </section>

          <section className="bottom-grid" id="scenarios">
            <article className="panel scenario-panel">
              <div className="panel-title"><div><span className="eyebrow">What-if lab</span><h2>Compare an intervention</h2></div></div>
              <form onSubmit={runScenario}>
                <label>Scenario name<input name="name" required placeholder="Shift backup traffic" /></label>
                <div className="form-grid"><label>Added capacity (Mbps)<input name="capacity" type="number" min="0" defaultValue="5000" /></label><label>Traffic reduction (%)<input name="reduction" type="number" min="0" max="95" defaultValue="10" /></label><label>Growth multiplier<input name="growth" type="number" min="0" max="5" step="0.1" defaultValue="1" /></label><label>Budget (USD)<input name="budget" type="number" min="0" placeholder="Optional" /></label></div>
                <button className="button primary" disabled={working || planLoading || !selectedLink}>{working ? 'Calculating…' : 'Run and save scenario'}</button>
              </form>
              <div className="scenario-list">{scenarios.length === 0 ? <p className="muted">No saved comparisons for this link.</p> : scenarios.slice().reverse().map((scenario) => <div className="scenario-result" key={scenario.id}><span><strong>{scenario.name}</strong><small>+{formatMbps(scenario.added_capacity_mbps)} · -{scenario.traffic_reduction_pct}% traffic</small></span><span><strong>{scenario.forecast?.risk.risk_level ?? '—'}</strong><small>{(scenario.risk_reduction_pct ?? 0).toFixed(1)} pt risk reduction</small></span></div>)}</div>
            </article>

            <article className="panel actions-panel">
              <div className="panel-title"><div><span className="eyebrow">Decision queue</span><h2>Recommended actions</h2></div></div>
              {forecast?.recommendations.map((recommendation) => <div className={`action-card ${recommendation.selected ? '' : 'excluded'}`} key={recommendation.id}><span className="action-icon">{recommendation.action === 'upgrade' ? '↑' : recommendation.action === 'shift_traffic' ? '⇄' : '◎'}</span><div><span className="action-meta">P{recommendation.priority} · {recommendation.action.replace('_', ' ')}</span><strong>{recommendation.description}</strong><p>{recommendation.impact}</p><small>{recommendation.selection_reason}</small></div><b>{recommendation.cost_estimate_usd ? `$${recommendation.cost_estimate_usd.toLocaleString()}` : 'No capex'}</b></div>)}
            </article>
          </section>
        </>}
      </main>
      <footer><span>Capacity Pilot · deterministic local planning mode</span><a href={DOCS_URL} target="_blank" rel="noreferrer">API documentation ↗</a></footer>
    </div>
  )
}

export default App
