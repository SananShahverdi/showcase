import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

const API = apiBase(import.meta.env.VITE_API_URL ?? 'http://localhost:8011/api')
type Finding = { id: string; severity: string; algorithm: string; source: string; line?: number; evidence?: string; rule_id: string; remediation: string; migration_priority: number }
type Inventory = { service_name: string; findings: Finding[]; posture: string; is_quantum_safe: boolean; retention_years: number; internet_exposed: boolean }
type Plan = { service_name: string; priority: number; rationale: string; target_state: string }
type ScanError = { service_name: string; source: string; code: string; message: string }
type Report = { id: string; rule_version: string; scanned_at: string; services: Inventory[]; migration_plan: Plan[]; errors: ScanError[]; total_findings: number; critical_findings: number; high_findings: number }

type ScanSummary = { id: string; scanned_at: string }
const severities = ['all', 'critical', 'high', 'medium', 'low', 'info']

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options })
  if (!response.ok) throw new Error(errorMessage((await response.json().catch(() => null))?.detail, response.status))
  return response.json() as Promise<T>
}

function App() {
  const [report, setReport] = useState<Report | null>(null)
  const [selected, setSelected] = useState('')
  const [severity, setSeverity] = useState('all')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  function show(value: Report) { setReport(value); setSelected(value.services[0]?.service_name ?? ''); setSeverity('all') }
  useEffect(() => {
    // The scan list is empty until something has been scanned, so the first visit makes no failing request.
    request<ScanSummary[]>('/scans')
      .then((scans) => scans.length ? request<Report>('/dashboard').then(show) : undefined)
      .catch((reason: Error) => setError(reason.message))
  }, [])
  async function scan() {
    setBusy(true); setError('')
    try { show(await request<Report>('/demo/seed', { method: 'POST' })) }
    catch (reason) { setError((reason as Error).message) } finally { setBusy(false) }
  }
  const inventory = report?.services.find((item) => item.service_name === selected) ?? report?.services[0]
  const findings = useMemo(() => (inventory?.findings ?? []).filter((finding) => severity === 'all' || finding.severity === severity), [inventory, severity])
  const severityCount = (item: string) => (inventory?.findings ?? []).filter((finding) => item === 'all' || finding.severity === item).length
  const posture = inventory?.posture.replaceAll('_', ' ') ?? 'not scanned'

  return <div className="shell crypto">
    <header className="topbar"><div className="brand"><span className="brand-mark" aria-hidden="true">Q</span><span>Quantum Ledger</span></div><nav aria-label="Sections"><a href="#inventory">Inventory</a><a href="#migration">Migration</a></nav><span className="status"><i aria-hidden="true" /> offline scanner ready</span></header>
    <main>
      <section className="intro"><div><p className="eyebrow">Cryptographic bill of materials · rules 2026.1</p><h1>Know what must change<br />before the deadline does.</h1><p className="lede">Trace classical cryptography to a file, line, TLS observation, and migration decision. Endpoint metadata is never invented.</p></div><div className="intro-action"><button className="primary" onClick={scan} disabled={busy}>{busy ? 'Scanning evidence…' : 'Load & scan demo estate'}</button><small>Two synthetic services with seeded TLS captures</small></div></section>
      {error && <div className="notice error" role="alert">{error}</div>}
      <section className="metrics" aria-label="Scan summary">
        <article><span>Services inventoried</span><strong>{report?.services.length ?? '—'}</strong><small>{report?.rule_version ? `rule set ${report.rule_version}` : 'awaiting scan'}</small></article>
        <article><span>Critical / high</span><strong className="danger">{report ? `${report.critical_findings} / ${report.high_findings}` : '—'}</strong><small>{report ? `of ${report.total_findings} findings` : 'prioritized exposure'}</small></article>
        <article><span>Coverage errors</span><strong>{report?.errors.length ?? '—'}</strong><small>never converted to fake evidence</small></article>
        <article><span>Migration items</span><strong className="accent">{report?.migration_plan.length ?? '—'}</strong><small>ordered by risk</small></article>
      </section>
      <div className="workspace inventory-workspace" id="inventory">
        <aside className="panel catalog" aria-label="Service inventory"><div className="panel-title"><span>Service inventory</span><b>{report?.services.length ?? 0}</b></div>{report?.services.map((service) => <button key={service.service_name} onClick={() => { setSelected(service.service_name); setSeverity('all') }} aria-pressed={selected === service.service_name} className={selected === service.service_name ? 'service active' : 'service'}><span className={`posture ${service.posture === 'action_required' ? 'bad' : service.is_quantum_safe ? 'good' : ''}`} role="img" aria-label={service.posture.replaceAll('_', ' ')} /><div><b>{service.service_name}</b><small>{service.findings.length} findings · {service.retention_years}y retention</small></div></button>)}{!report && <div className="empty">Run the demo scan, or submit services to <code>POST /api/scan</code>.</div>}</aside>
        <section className="panel lab" aria-label="Evidence explorer">
          <div className="panel-title"><div><span>{inventory?.service_name ?? 'Evidence explorer'}</span><small>{inventory ? `${inventory.internet_exposed ? 'Internet exposed' : 'Internal'} · ${inventory.retention_years} year data horizon` : 'Select a scanned service'}</small></div><span className={`tag ${posture.includes('action') ? 'tag-bad' : ''}`}>{posture}</span></div>
          <div className="filter-row" role="group" aria-label="Filter findings by severity"><span>Severity</span>{severities.map((item) => <button key={item} onClick={() => setSeverity(item)} aria-pressed={severity === item} disabled={!inventory || (item !== 'all' && !severityCount(item))} className={severity === item ? 'filter active' : 'filter'}>{item} <em>{inventory ? severityCount(item) : 0}</em></button>)}</div>
          <div className="evidence-table"><div className="table-head"><span>Risk</span><span>Algorithm & evidence</span><span>Location</span><span>Rule</span></div>{findings.map((finding) => <div className="table-row" key={finding.id}><span><b className={`severity ${finding.severity}`}>{finding.severity}</b><small title="Migration priority, 0-100">P{finding.migration_priority}</small></span><span><b>{finding.algorithm}</b><small title={finding.evidence}>{finding.evidence || 'No excerpt retained'}</small></span><span><code>{finding.source}{finding.line ? `:${finding.line}` : ''}</code></span><span><code>{finding.rule_id}</code></span><p className="remediation"><b>Remediation</b> {finding.remediation}</p></div>)}{inventory && !findings.length && <div className="empty">No evidence matches this filter.</div>}{!inventory && <div className="empty">Findings appear here with file, line, and rule evidence after a scan.</div>}</div>
        </section>
      </div>
      <section className="results" id="migration"><div className="section-heading"><div><p className="eyebrow">Ordered action plan</p><h2>Migration runway</h2></div>{report ? <div className="exports"><span>scan {report.id.slice(0, 8)} · {new Date(report.scanned_at).toLocaleString()}</span><a href={`${API}/scans/${report.id}/export?format=markdown`} download={`pqc-scan-${report.id.slice(0, 8)}.md`}>Export Markdown</a><a href={`${API}/scans/${report.id}/export?format=json`} download={`pqc-scan-${report.id.slice(0, 8)}.json`}>Export JSON</a></div> : <span>No scan yet</span>}</div><div className="plan-grid">{report?.migration_plan.map((item, index) => <article className="plan" key={item.service_name}><span className="rank">{String(index + 1).padStart(2, '0')}</span><div><div className="result-head"><b>{item.service_name}</b><span className="pill bad">priority {item.priority}</span></div><p>{item.rationale}</p><small>{item.target_state}</small></div></article>)}{report && !report.migration_plan.length && <div className="empty">No actionable item detected. Verify inventory coverage before concluding readiness.</div>}{!report && <div className="empty">The migration order is computed from severity, internet exposure, and data-retention horizon.</div>}</div>{report?.errors.map((item) => <div className="notice" key={`${item.service_name}-${item.source}-${item.code}`}>Coverage gap · <b>{item.service_name}</b> · {item.message}</div>)}</section>
    </main>
  </div>
}

export default App
