import { useEffect, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

const API = apiBase(import.meta.env.VITE_API_URL ?? 'http://localhost:8007/api')
const seededDiff = `diff --git a/src/auth.py b/src/auth.py
--- a/src/auth.py
+++ b/src/auth.py
@@ -18,2 +18,4 @@
+def new_feature(payload):
+    return eval(payload)
+    # password = "demo-secret"
 return True`

type Finding = { rule_id: string; category: string; severity: string; file_path?: string; line_number?: number; message: string; remediation?: string }
type Report = { id: string; pr_id: string; repo: string; title?: string; status: string; created_at: string; llm_summary: string; policy_reasons: string[]; llm_comments: { file_path: string; line_range: string; comment: string }[]; analysis_result: { findings: Finding[]; tests_passed: boolean; coverage_percent: number; changed_files: string[]; tool_statuses: Record<string, string> } }
type Summary = { total_reviews: number; approved: number; changes_requested: number; blocked: number; pass_rate: number; recurring_rules: Record<string, number> }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) throw new Error(errorMessage((await response.json().catch(() => null))?.detail, response.status))
  return response.json() as Promise<T>
}

function App() {
  const [repo, setRepo] = useState('acme/checkout')
  const [prId, setPrId] = useState('pr-284')
  const [title, setTitle] = useState('Harden authentication flow')
  const [coverage, setCoverage] = useState(86)
  const [diff, setDiff] = useState(seededDiff)
  const [reports, setReports] = useState<Report[]>([])
  const [summary, setSummary] = useState<Summary>({ total_reviews: 0, approved: 0, changes_requested: 0, blocked: 0, pass_rate: 0, recurring_rules: {} })
  const [active, setActive] = useState<Report | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const refresh = async () => {
    const [history, totals] = await Promise.all([request<Report[]>('/dashboard/reports'), request<Summary>('/dashboard/summary')])
    setReports(history); setSummary(totals)
  }
  useEffect(() => { refresh().catch((reason: Error) => setError(reason.message)) }, [])

  // Open the first item once data arrives, so the detail panel is never an empty prompt.
  useEffect(() => { if (!active && reports.length) setActive(reports[0]) }, [reports, active])

  const review = async () => {
    setBusy(true); setError('')
    try {
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify({ diff, coverage })))
      const revision = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
      const report = await request<Report>('/reviews/local', { method: 'POST', body: JSON.stringify({ id: prId, repo, title, diff_content: diff, head_sha: revision, reported_coverage_percent: coverage }) })
      setActive(report); await refresh()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Review failed') }
    finally { setBusy(false) }
  }

  const rules = Object.entries(summary.recurring_rules).slice(0, 4)
  // Line comments that restate a finding are already shown above; keep only extra guidance.
  const findingText = new Set(active?.analysis_result.findings.map((finding) => `[${finding.rule_id}] ${finding.message}`))
  const guidance = active?.llm_comments.filter((comment) => !findingText.has(comment.comment)) ?? []
  const missing = [!repo.trim() && 'repository', !prId.trim() && 'pull request', !title.trim() && 'title', !diff.trim() && 'diff'].filter(Boolean)
  return (
    <main className="app-shell">
      <header className="topbar"><div className="brand"><span className="brand-mark">//</span><span>Gatehouse</span></div><nav><a href="#submit">Review</a><a href="#history">History</a><a href="#policy">Policy</a></nav><div className="user-chip">Local analyzer</div></header>
      <section className="hero-band"><div><p className="eyebrow">PR QUALITY CONTROL</p><h1>Ground every gate.</h1><p>Changed-line analysis, deterministic security checks, and policy decisions your team can reproduce.</p></div><span className="policy-pill">Policy v1 · 80% coverage</span></section>
      <section className="stats"><div><span>Total reviews</span><strong>{summary.total_reviews}</strong></div><div><span>Pass rate</span><strong>{summary.total_reviews ? `${Math.round(summary.pass_rate * 100)}%` : '—'}</strong></div><div><span>Blocked</span><strong>{summary.blocked}</strong></div><div><span>Changes requested</span><strong>{summary.changes_requested}</strong></div></section>
      {error && <div className="notice" role="alert">{error}</div>}
      <section className="workspace" id="submit">
        <section className="panel submit-panel">
          <div className="panel-heading"><div><p className="eyebrow">LOCAL DIFF</p><h2>Run a review</h2></div><span className="safe-label">Offline ready</span></div>
          <div className="form-grid"><label>Repository<input value={repo} onChange={(event) => setRepo(event.target.value)} /></label><label>Pull request<input value={prId} onChange={(event) => setPrId(event.target.value)} /></label><label className="wide">Title<input value={title} onChange={(event) => setTitle(event.target.value)} /></label><label className="wide">Reported coverage <b>{coverage}%</b><input type="range" min="0" max="100" value={coverage} onChange={(event) => setCoverage(Number(event.target.value))} /></label><label className="wide">Unified diff<textarea value={diff} onChange={(event) => setDiff(event.target.value)} rows={14} spellCheck={false} /></label></div>
          <button onClick={review} disabled={busy || missing.length > 0} aria-describedby={missing.length ? 'submit-hint' : undefined}>{busy ? 'Analyzing changed lines…' : 'Run policy gate'}</button>
          {missing.length > 0 && <p className="form-hint" id="submit-hint">Add a {missing.join(', ')} to run the gate.</p>}
        </section>
        <section className="panel result-panel">
          {!active ? <div className="empty-state"><span>⌘</span><h2>No active report</h2><p>Submit the seeded diff or open a historical review.</p></div> : <>
            <div className="panel-heading"><div><p className="eyebrow">{active.repo} · {active.pr_id}</p><h2>Gate result</h2>{active.title && <p className="report-title">{active.title}</p>}</div><span className={`status ${active.status}`}>{active.status.replaceAll('_', ' ')}</span></div>
            <p className="summary-copy">{active.llm_summary}</p>
            <div className="reason-box"><b>Policy decision</b>{active.policy_reasons.map((reason) => <span key={reason}>↳ {reason}</span>)}</div>
            <div className="tool-grid" aria-label="Analyzer results">{Object.entries(active.analysis_result.tool_statuses).map(([tool, status]) => <div key={tool}><span>{tool}</span><b className={status}>{status}</b></div>)}</div>
            <div className="section-title"><h3>Grounded findings</h3><span>{active.analysis_result.findings.length}</span></div>
            {active.analysis_result.findings.length === 0 ? <p className="empty">No rule findings on added lines.</p> : active.analysis_result.findings.map((finding) => <article className="finding" key={`${finding.rule_id}-${finding.line_number}`}><div className="finding-top"><span className={`severity ${finding.severity}`}>{finding.severity}</span><code>{finding.file_path}:{finding.line_number}</code></div><b>{finding.rule_id}</b><p>{finding.message}</p><small>{finding.remediation}</small></article>)}
            {guidance.length > 0 && <><div className="section-title"><h3>Reviewer guidance</h3><span>{guidance.length}</span></div><ul className="comment-list">{guidance.map((comment, index) => <li key={`${comment.file_path}-${comment.line_range}-${index}`}><code>{comment.file_path}:{comment.line_range}</code><span>{comment.comment}</span></li>)}</ul></>}
          </>}
        </section>
      </section>
      <section className="lower-grid" id="history"><section className="panel"><div className="panel-heading"><div><p className="eyebrow">EVIDENCE</p><h2>Review history</h2></div><span>{reports.length} runs</span></div><div className="history-list">{reports.length === 0 && <p className="empty">No review history yet.</p>}{reports.map((report) => <button key={report.id} className={active?.id === report.id ? 'active' : ''} aria-pressed={active?.id === report.id} onClick={() => setActive(report)}><span><b>{report.title || report.repo}</b><small>{report.repo} · {report.pr_id} · {new Date(report.created_at).toLocaleString()}</small></span><span className={`status ${report.status}`}>{report.status.replaceAll('_', ' ')}</span></button>)}</div></section><section className="panel" id="policy"><p className="eyebrow">RECURRING RISK</p><h2>Rule frequency</h2>{rules.length === 0 ? <p className="empty">Rules appear here as reviews accumulate.</p> : <div className="rules">{rules.map(([rule, count]) => <div key={rule}><span>{rule}</span><b>{count}</b></div>)}</div>}</section></section>
    </main>
  )
}

export default App
