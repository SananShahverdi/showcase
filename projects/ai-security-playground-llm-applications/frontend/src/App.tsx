import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

const API = apiBase(import.meta.env.VITE_API_URL ?? 'http://localhost:8010/api')

type Mode = 'vulnerable' | 'hardened'
type Scenario = {
  id: string; name: string; type: string; description: string; attack_payload: string
  threat: string; mitigation_description: string; allowed_tools_by_role: Record<string, string[]>
}
type Decision = { control_id: string; effect: string; reason: string }
type Result = {
  id: string; mode: Mode; scenario_type: string; role: string; was_successful_attack: boolean
  mitigation_triggered: boolean; output: string; tools_called: string[]; requested_tools: string[]
  controls_triggered: string[]; decisions: Decision[]; duration_ms: number; approval_id?: string
}
type Report = { id: string; scenarios_tested: number; vulnerabilities_found: number; mitigations_verified: number; mitigation_rate: number; results: Result[]; created_at: string }
type Metrics = { total_runs: number; blocked_runs: number; successful_attacks: number; pending_approvals: number }

// The newest recorded run of each mode for one scenario (history is newest first).
function latestPerMode(history: Result[], scenarioType: string): Result[] {
  return (['vulnerable', 'hardened'] as Mode[]).flatMap((mode) => history.find((item) => item.scenario_type === scenarioType && item.mode === mode) ?? [])
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options })
  if (!response.ok) throw new Error(errorMessage((await response.json().catch(() => null))?.detail, response.status))
  return response.json() as Promise<T>
}

function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [payload, setPayload] = useState('')
  const [role, setRole] = useState('learner')
  const [results, setResults] = useState<Result[]>([])
  const [history, setHistory] = useState<Result[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const selected = useMemo(() => scenarios.find((scenario) => scenario.id === selectedId), [scenarios, selectedId])
  const refreshMetrics = () => request<Metrics>('/metrics').then(setMetrics)
  useEffect(() => {
    // Load the catalog together with the stored evidence, so the latest assessment and
    // the first scenario's most recent traces are visible without re-running anything.
    Promise.all([request<Scenario[]>('/scenarios'), request<Report[]>('/assessments?limit=1'), request<Result[]>('/runs?limit=200'), request<Metrics>('/metrics')])
      .then(([items, reports, runs, summary]) => {
        setScenarios(items); setSelectedId(items[0]?.id ?? ''); setPayload(items[0]?.attack_payload ?? '')
        setReport(reports[0] ?? null); setHistory(runs); setMetrics(summary)
        if (items[0]) setResults(latestPerMode(runs, items[0].type))
      }).catch((reason: Error) => setError(reason.message))
  }, [])

  function choose(scenario: Scenario) { setSelectedId(scenario.id); setPayload(scenario.attack_payload); setResults(latestPerMode(history, scenario.type)) }
  async function run(modes: Mode[]) {
    if (!selected) return
    setBusy(true); setError('')
    try {
      const outcomes = await Promise.allSettled(modes.map((mode) => request<Result>(`/execute/${selected.id}`, {
        method: 'POST', body: JSON.stringify({ mode, payload, role }),
      })))
      const completed = outcomes.flatMap((outcome) => outcome.status === 'fulfilled' ? [outcome.value] : [])
      setResults((current) => [...completed, ...current.filter((item) => !modes.includes(item.mode))])
      setHistory((current) => [...completed, ...current])
      await refreshMetrics()
      const failed = outcomes.find((outcome) => outcome.status === 'rejected')
      if (failed?.status === 'rejected') throw failed.reason
    } catch (reason) { setError((reason as Error).message) } finally { setBusy(false) }
  }
  async function compare() { await run(['vulnerable', 'hardened']) }
  async function assess() {
    setBusy(true); setError('')
    try {
      const created = await request<Report>('/assessment', { method: 'POST' })
      setReport(created)
      const runs = [...created.results].reverse()
      setHistory((current) => [...runs, ...current])
      if (selected) setResults(latestPerMode(runs, selected.type))
      await refreshMetrics()
    }
    catch (reason) { setError((reason as Error).message) } finally { setBusy(false) }
  }

  return <div className="shell">
    <header className="topbar"><div className="brand"><span className="brand-mark">AS</span><span>AgentShield Lab</span></div><span className="status"><i /> synthetic sandbox</span></header>
    <main>
      <section className="intro">
        <div><p className="eyebrow">AI application security · policy 2026.1</p><h1>See the exploit. Inspect the control.</h1><p className="lede">Run the same hostile input against an intentionally vulnerable training agent and a hardened, policy-traced agent. No real tool can reach your host.</p></div>
        <div className="intro-actions"><button className="secondary" onClick={assess} disabled={busy}>Run full assessment</button>{report && <p className="export">Report {new Date(report.created_at).toLocaleString()} · <a href={`${API}/assessment/${report.id}/export?format=markdown`} target="_blank" rel="noreferrer">Markdown</a> · <a href={`${API}/assessment/${report.id}/export?format=json`} target="_blank" rel="noreferrer">JSON</a></p>}</div>
      </section>
      <section className="metrics">
        <article><span>Scenario coverage</span><strong>{report ? `${report.scenarios_tested}/${scenarios.length}` : scenarios.length || '—'}</strong><small>versioned attack cases</small></article>
        <article><span>Exposures demonstrated</span><strong className="danger">{report?.vulnerabilities_found ?? '—'}</strong><small>synthetic effects only</small></article>
        <article><span>Mitigations verified</span><strong className="safe">{report ? `${Math.round(report.mitigation_rate * 100)}%` : '—'}</strong><small>{report ? `${report.mitigations_verified} of ${report.scenarios_tested} hardened runs blocked` : 'run an assessment'}</small></article>
        <article><span>Pending approvals</span><strong>{metrics?.pending_approvals ?? '—'}</strong><small>{metrics ? `${metrics.total_runs} runs recorded · ${metrics.blocked_runs} blocked` : 'one-time human review'}</small></article>
      </section>
      {error && <div className="notice error" role="alert">{error}</div>}
      <div className="workspace">
        <aside className="panel catalog"><div className="panel-title"><span>Attack library</span><b>{scenarios.length}</b></div>{scenarios.map((scenario, index) => <button key={scenario.id} className={scenario.id === selectedId ? 'scenario active' : 'scenario'} disabled={busy} onClick={() => choose(scenario)}><span>{String(index + 1).padStart(2, '0')}</span><div><b>{scenario.name}</b><small>{scenario.type.replaceAll('_', ' ')}</small></div></button>)}</aside>
        <section className="panel lab">
          {selected ? <>
            <div className="panel-title"><div><span>{selected.name}</span><small>{selected.threat}</small></div><span className="tag">{selected.type.replaceAll('_', ' ')}</span></div>
            <label>Attack payload<textarea disabled={busy} value={payload} onChange={(event) => setPayload(event.target.value)} rows={5} /></label>
            <div className="controls"><label>Execution role<select disabled={busy} value={role} onChange={(event) => setRole(event.target.value)}><option value="learner">Learner</option><option value="developer">Developer</option><option value="security_admin">Security admin</option></select></label><div className="actions"><button className="ghost danger-button" disabled={busy} onClick={() => run(['vulnerable'])}>Run vulnerable</button><button className="primary" disabled={busy} onClick={compare}>{busy ? 'Running…' : 'Compare both modes'}</button></div></div>
            <div className="permission"><span>Allowed for {role}</span><code>{selected.allowed_tools_by_role[role]?.join(', ') || 'no tools'}</code></div>
            <p className="mitigation"><b>Expected control</b>{selected.mitigation_description}</p>
          </> : <div className="empty">Connect the API to load the versioned attack library.</div>}
        </section>
      </div>
      <section className="results">
        <div className="section-heading"><div><p className="eyebrow">Execution evidence</p><h2>Side-by-side trace</h2></div><span>{results.length ? `Latest ${results.length === 2 ? 'vulnerable and hardened runs' : `${results[0].mode} run`} for this scenario` : 'Run a comparison to begin'}</span></div>
        <div className="result-grid">{(['vulnerable', 'hardened'] as Mode[]).map((mode) => {
          const result = results.find((item) => item.mode === mode)
          return <article className={`result ${mode}`} key={mode}><div className="result-head"><b>{mode}</b>{result && <span className={result.was_successful_attack ? 'pill bad' : 'pill good'}>{result.was_successful_attack ? 'attack succeeded' : 'attack blocked'}</span>}</div>{result ? <><pre>{result.output}</pre><dl><div><dt>Requested</dt><dd>{result.requested_tools.join(', ') || 'none'}</dd></div><div><dt>Executed</dt><dd>{result.tools_called.join(', ') || 'none'}</dd></div><div><dt>Latency</dt><dd>{result.duration_ms.toFixed(2)} ms</dd></div></dl><ol className="timeline">{result.decisions.map((decision) => <li key={decision.control_id}><span>{decision.effect}</span><div><b>{decision.control_id}</b><p>{decision.reason}</p></div></li>)}</ol>{result.approval_id && <div className="notice">Pending approval <code>{result.approval_id.slice(0, 8)}</code></div>}</> : <div className="empty">No {mode} trace yet.</div>}</article>
        })}</div>
      </section>
    </main>
  </div>
}

export default App
