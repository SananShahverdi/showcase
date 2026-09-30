import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

const API = apiBase(import.meta.env.VITE_API_URL ?? 'http://localhost:8013/api')
type Version = { id: string; version_tag: string; artifact_sha256: string; status: string; canary_passed: boolean; manifest: { runtime_kind: string; local_adapter?: string; abi_version: string }; validation_findings: { code: string; message: string }[] }
type Plugin = { id: string; name: string; description: string; active_version_id?: string; versions: Version[]; limits: { max_memory_mb: number; timeout_ms: number; fuel: number; max_input_bytes: number; max_output_bytes: number }; activation_history: unknown[] }
type Execution = { id: string; plugin_id: string; version_tag: string; runtime_kind: string; runtime_provenance: string; input_sha256: string; status: string; output_payload?: Record<string, unknown>; error_message?: string; latency_ms: number }
type Capabilities = { wasmtime_available: boolean; wasm_execution_ready: boolean; trusted_local_adapters: string[]; abi_version: string }
type Metrics = { executions: number; errors: number; error_rate: number; p50_latency_ms: number; p95_latency_ms: number }

// Example inputs for the seeded plugins; any JSON object can be submitted.
const samples: Record<string, string> = {
  'json-normalizer': '{\n  "message": "HELLO FROM WASM",\n  "Region": "EU-WEST"\n}',
  'data-cleaner': '{\n  "customer": "  ADA LOVELACE  ",\n  "region": " EU "\n}',
  'alert-filter': '{\n  "severity": "low",\n  "signal": "cpu-noise"\n}',
  'routing-policy': '{\n  "region": "EU",\n  "request_id": "demo-42"\n}',
}
const fallbackSample = '{\n  "key": "value"\n}'
// Open on the real WebAssembly example when it is registered.
const preferred = (items: Plugin[]) => items.find((item) => item.id === 'json-normalizer' && item.active_version_id) ?? items[0]

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options })
  if (!response.ok) throw new Error(errorMessage((await response.json().catch(() => null))?.detail, response.status))
  return response.json() as Promise<T>
}

function App() {
  const [plugins, setPlugins] = useState<Plugin[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [payload, setPayload] = useState(fallbackSample)
  const [execution, setExecution] = useState<Execution | null>(null)
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  function choose(plugin: Plugin) {
    setSelectedId(plugin.id); setExecution(null); setMetrics(null); setError('')
    setPayload(samples[plugin.id] ?? fallbackSample)
  }
  useEffect(() => {
    request<Capabilities>('/runtime/capabilities').then(setCapabilities).catch((reason: Error) => setError(reason.message))
    request<Plugin[]>('/plugins').then((items) => { setPlugins(items); const first = preferred(items); if (first) choose(first) }).catch((reason: Error) => setError(reason.message))
  }, [])
  const selected = useMemo(() => plugins.find((plugin) => plugin.id === selectedId), [plugins, selectedId])
  const active = selected?.versions.find((version) => version.id === selected.active_version_id)
  async function seed() {
    setBusy(true); setError('')
    try { const items = await request<Plugin[]>('/demo/seed', { method: 'POST' }); setPlugins(items); const first = preferred(items); if (first) choose(first) }
    catch (reason) { setError((reason as Error).message) } finally { setBusy(false) }
  }
  async function execute() {
    if (!selected || !active) return
    let parsed: unknown
    try { parsed = JSON.parse(payload) } catch (reason) { setError(`Input is not valid JSON: ${(reason as Error).message}`); return }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) { setError('Input must be a JSON object, for example {"key": "value"}.'); return }
    setBusy(true); setError('')
    try {
      setExecution(await request<Execution>('/execute', { method: 'POST', body: JSON.stringify({ plugin_id: selected.id, payload: parsed }) }))
      setMetrics(await request<Metrics>(`/plugins/${encodeURIComponent(selected.id)}/versions/${encodeURIComponent(active.version_tag)}/metrics`))
    } catch (reason) { setError((reason as Error).message) } finally { setBusy(false) }
  }
  const runtimeLabel = !capabilities ? 'checking runtime' : capabilities.wasm_execution_ready ? 'wasmtime ready' : 'wasm offline · adapters only'

  return <div className="shell wasm">
    <header className="topbar"><div className="brand"><span className="brand-mark" aria-hidden="true">W</span><span>EdgeForge</span></div><nav aria-label="Sections"><a href="#registry">Registry</a><a href="#executions">Executions</a><a href="#runtime">Runtime</a></nav><span className={`status ${capabilities && !capabilities.wasm_execution_ready ? 'status-warn' : ''}`}><i aria-hidden="true" /> {runtimeLabel}</span></header>
    <main>
      <section className="intro"><div><p className="eyebrow">Typed edge-rule control plane · ABI edge-json-v1</p><h1>Ship rules to the edge.<br />Keep the host out of reach.</h1><p className="lede">Validate immutable artifacts, canary every promotion, execute under explicit limits, and roll back through activation history.</p></div><button className="primary" onClick={seed} disabled={busy}>{busy ? 'Preparing registry…' : 'Seed trusted examples'}</button></section>
      {error && <div className="notice error" role="alert">{error}</div>}
      <section className="metrics" id="runtime">
        <article><span>Registered plugins</span><strong>{plugins.length || '—'}</strong><small>immutable version registry</small></article>
        <article><span>Wasm runtime</span><strong className={capabilities?.wasm_execution_ready ? 'safe' : 'danger'}>{capabilities?.wasmtime_available ? 'detected' : 'offline'}</strong><small>{capabilities?.wasm_execution_ready ? 'execution ready' : 'fails closed'}</small></article>
        <article><span>Default imports</span><strong>0</strong><small>WASI · network · filesystem denied</small></article>
        <article><span>Trusted adapters</span><strong className="accent">{capabilities?.trusted_local_adapters.length ?? '—'}</strong><small>explicitly non-Wasm</small></article>
      </section>
      <div className="workspace wasm-workspace" id="registry">
        <aside className="panel catalog"><div className="panel-title"><span>Plugin registry</span><b>{plugins.length}</b></div>{plugins.map((plugin) => <button key={plugin.id} onClick={() => choose(plugin)} aria-pressed={selectedId === plugin.id} className={selectedId === plugin.id ? 'service active' : 'service'}><span className="plugin-icon" aria-hidden="true">{plugin.name.slice(0, 1)}</span><div><b>{plugin.name}</b><small>{plugin.versions.find((version) => version.id === plugin.active_version_id)?.manifest.runtime_kind === 'wasm' ? 'WebAssembly' : 'trusted adapter'} · {plugin.versions.length} version(s) · {plugin.active_version_id ? 'active' : 'inactive'}</small></div></button>)}{!plugins.length && <div className="empty">Seed the three trusted local adapters or register a Wasm artifact through the API.</div>}</aside>
        <section className="panel lab">
          <div className="panel-title"><div><span>{selected?.name ?? 'Execution workbench'}</span><small>{selected?.description ?? 'Select a plugin to inspect its contract.'}</small></div>{active && <span className="tag">{active.manifest.runtime_kind.replace('_', ' ')} · {active.version_tag}</span>}</div>
          {selected ? <><label>JSON input<textarea value={payload} onChange={(event) => setPayload(event.target.value)} rows={9} spellCheck={false} /></label><div className="limit-grid"><div><span>Memory</span><b>{selected.limits.max_memory_mb} MB</b></div><div><span>Timeout</span><b>{selected.limits.timeout_ms} ms</b></div><div><span>Fuel</span><b>{selected.limits.fuel.toLocaleString()}</b></div><div><span>I/O cap</span><b>{Math.round(selected.limits.max_output_bytes / 1000)} KB</b></div></div>{!active && <p className="hint">This plugin has no active version. Canary and activate one through the API first.</p>}<button className="primary execute" onClick={execute} disabled={busy || !active}>{busy ? 'Executing…' : 'Execute active version'}</button></> : <div className="empty">No active plugin. Seed examples to exercise the complete local lifecycle.</div>}
        </section>
      </div>
      <section className="results" id="executions"><div className="section-heading"><div><p className="eyebrow">Runtime evidence</p><h2>Execution & provenance</h2></div><span>{execution ? execution.id.slice(0, 8) : 'No execution yet'}</span></div><div className="execution-grid"><article className="result"><div className="result-head"><b>Output</b>{execution && <span className={execution.status === 'success' ? 'pill good' : 'pill bad'}>{execution.status}</span>}</div>{execution ? <><pre>{JSON.stringify(execution.output_payload ?? { error: execution.error_message }, null, 2)}</pre><dl><div><dt>Runtime</dt><dd>{execution.runtime_kind}</dd></div><div><dt>Provenance</dt><dd>{execution.runtime_provenance}</dd></div><div><dt>Latency</dt><dd>{execution.latency_ms.toFixed(3)} ms</dd></div><div><dt>Input hash</dt><dd><code>{execution.input_sha256.slice(0, 16)}…</code></dd></div></dl>{metrics && <dl className="metrics-row" aria-label="Recorded executions of this version"><div><dt>Recorded runs</dt><dd>{metrics.executions}</dd></div><div><dt>Error rate</dt><dd>{(metrics.error_rate * 100).toFixed(1)}%</dd></div><div><dt>p50 latency</dt><dd>{metrics.p50_latency_ms.toFixed(3)} ms</dd></div><div><dt>p95 latency</dt><dd>{metrics.p95_latency_ms.toFixed(3)} ms</dd></div></dl>}</> : <div className="empty">Execution output is bounded, parsed as JSON, and recorded without raw input.</div>}</article><article className="result versions"><div className="result-head"><b>Version policy</b><span>{selected?.activation_history.length ?? 0} activation(s)</span></div>{selected?.versions.map((version) => <div className="version" key={version.id}><span className={version.status === 'validated' ? 'posture good' : 'posture bad'} /><div><b>{version.version_tag} · {version.manifest.runtime_kind.replace('_', ' ')}</b><small><code>{version.artifact_sha256.slice(0, 16)}…</code> · {version.canary_passed ? 'canary passed' : 'canary required'}</small>{version.validation_findings.map((finding) => <p key={finding.code}>{finding.code}: {finding.message}</p>)}</div></div>) ?? <div className="empty">No versions registered.</div>}</article></div></section>
    </main>
  </div>
}

export default App
