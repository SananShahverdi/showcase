import { useEffect, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

const API = apiBase(import.meta.env.VITE_API_URL ?? 'http://localhost:8008/api')
const ORIGIN = API.replace(/\/api\/?$/, '')
type Template = { id: string; name: string; version: string; description: string; status: string; parameters: Record<string, string> }
type Service = { id: string; name: string; owner: string; description: string; template_id: string; template_version: string; lifecycle: string; dependencies: string[]; runbook_url?: string }
type Artifact = { service_id: string; download_url: string; manifest_url: string; files_generated: number; checksum_sha256: string }
type Manifest = { service_id: string; template_id: string; template_version: string; checksum_sha256: string; files: Record<string, string> }
// Evidence for one stored archive: a service just generated, or one selected from the catalog.
type Evidence = { name: string; generated: boolean; manifest: Manifest }
const artifactLinks = (serviceId: string) => ({ download: `${ORIGIN}/api/download/${serviceId}`, manifest: `${ORIGIN}/api/artifacts/${serviceId}/manifest` })

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...init, headers: { 'Content-Type': 'application/json', 'x-role': 'developer', ...init?.headers } })
  if (!response.ok) throw new Error(errorMessage((await response.json().catch(() => null))?.detail, response.status))
  return response.json() as Promise<T>
}

function App() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [services, setServices] = useState<Service[]>([])
  const [templateId, setTemplateId] = useState('fastapi-base')
  const [serviceName, setServiceName] = useState('risk-api')
  const [owner, setOwner] = useState('team-risk')
  const [port, setPort] = useState('8080')
  const [preview, setPreview] = useState<string[]>([])
  const [artifact, setArtifact] = useState<Evidence | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const refresh = async () => {
    const [available, catalog] = await Promise.all([request<Template[]>('/templates'), request<Service[]>('/catalog')])
    setTemplates(available); setServices(catalog)
    return catalog
  }
  const showArtifact = async (service: Pick<Service, 'id' | 'name'>, generated: boolean) => {
    const manifest = await request<Manifest>(`/artifacts/${service.id}/manifest`)
    setPreview([]); setArtifact({ name: service.name, generated, manifest })
  }
  const inspect = async (service: Service) => {
    setBusy(true); setError('')
    try { await showArtifact(service, false) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load the artifact manifest') }
    finally { setBusy(false) }
  }
  useEffect(() => {
    // Open the most recently registered service's stored artifact so its evidence is visible immediately.
    refresh().then((catalog) => { const latest = catalog.at(-1); return latest ? showArtifact(latest, false) : undefined })
      .catch((reason: Error) => setError(reason.message))
  }, [])

  const payload = () => ({ template_id: templateId, service_name: serviceName, owner, description: `${serviceName} generated from an approved golden path`, parameters: { port } })
  const runPreview = async () => {
    setBusy(true); setError('')
    try { setArtifact(null); setPreview((await request<{ files: string[] }>('/scaffold/preview', { method: 'POST', body: JSON.stringify(payload()) })).files) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Preview failed') }
    finally { setBusy(false) }
  }
  const scaffold = async () => {
    setBusy(true); setError('')
    try { const created = await request<Artifact>('/scaffold', { method: 'POST', body: JSON.stringify(payload()) }); await showArtifact({ id: created.service_id, name: serviceName }, true); await refresh() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Scaffolding failed') }
    finally { setBusy(false) }
  }

  const selected = templates.find((template) => template.id === templateId)
  return (
    <main className="app-shell">
      <header className="topbar"><div className="brand"><span className="mark">P</span><span>Pathfinder</span></div><nav><a href="#templates">Templates</a><a href="#create">Create</a><a href="#catalog">Catalog</a></nav><span className="role">developer · local</span></header>
      <section className="hero"><div><p className="eyebrow">INTERNAL DEVELOPER PLATFORM</p><h1>Ship on the paved road.</h1><p>Approved service foundations, transparent quality defaults, and downloadable artifacts that actually exist.</p></div><div className="hero-metric"><strong>{templates.filter((template) => template.status === 'approved').length}</strong><span>approved paths</span></div></section>
      {error && <div className="notice" role="alert">{error}</div>}
      <section id="templates" className="template-strip">{templates.map((template) => <button key={template.id} className={template.id === templateId ? 'active' : ''} onClick={() => { setTemplateId(template.id); setPreview([]); setArtifact(null) }}><span className="template-icon">{template.name.slice(0, 2).toUpperCase()}</span><span><b>{template.name}</b><small>v{template.version} · {template.status}</small></span></button>)}</section>
      <section className="workspace" id="create">
        <section className="panel create-panel"><div className="panel-heading"><div><p className="eyebrow">GOLDEN PATH</p><h2>Create a component</h2></div><span className="step">01 / Configure</span></div><div className="selected-template"><span className="template-icon large">{selected?.name.slice(0, 2).toUpperCase()}</span><div><b>{selected?.name}</b><p>{selected?.description}</p></div><span className="approved">✓ approved</span></div><div className="form-grid"><label>Service name<input value={serviceName} onChange={(event) => { setServiceName(event.target.value); setPreview([]); setArtifact(null) }} /><small>Lowercase DNS label, 3–63 characters</small></label><label>Owner<input value={owner} onChange={(event) => { setOwner(event.target.value); setPreview([]); setArtifact(null) }} /></label><label>Port<input value={port} inputMode="numeric" onChange={(event) => { setPort(event.target.value); setPreview([]); setArtifact(null) }} /></label><label>Lifecycle<input value="experimental" disabled /></label></div><div className="button-row"><button className="secondary" onClick={runPreview} disabled={busy}>Preview files</button><button onClick={scaffold} disabled={busy}>{busy ? 'Validating & packaging…' : 'Generate artifact'}</button></div></section>
        <aside className="panel result-panel"><div className="panel-heading"><div><p className="eyebrow">OUTPUT</p><h2>Artifact evidence</h2></div></div>{artifact ? <div className="artifact-success">{artifact.generated && <span className="success-mark" aria-hidden="true">✓</span>}<h3>{artifact.generated ? `${artifact.name} is ready` : artifact.name}</h3><p>{artifact.generated ? 'Generated just now' : 'Stored catalog artifact'} · {artifact.manifest.template_id}@{artifact.manifest.template_version} · {Object.keys(artifact.manifest.files).length} files</p><div className="file-list manifest-files" aria-label="Files and SHA-256 digests">{Object.entries(artifact.manifest.files).map(([file, digest]) => <code key={file}><span>{file}</span><span title={digest}>{digest.slice(0, 10)}</span></code>)}</div><p className="checksum-label">Archive SHA-256</p><code>{artifact.manifest.checksum_sha256}</code><a className="download" href={artifactLinks(artifact.manifest.service_id).download}>Download ZIP</a><a className="manifest" href={artifactLinks(artifact.manifest.service_id).manifest} target="_blank" rel="noreferrer">Open manifest ↗</a></div> : preview.length ? <div><p className="preview-title">Validated file manifest</p><div className="file-list">{preview.map((file) => <code key={file}>{file}</code>)}</div><p className="hint">Generation stores this exact file set before registering the catalog record.</p></div> : <div className="empty-state"><span>▱</span><h3>Preview or generate</h3><p>Validated paths, checksum, and download controls will appear here.</p></div>}</aside>
      </section>
      <section className="panel catalog" id="catalog"><div className="panel-heading"><div><p className="eyebrow">OWNERSHIP & DEPENDENCIES</p><h2>Service catalog</h2></div><span className="count">{services.length} components</span></div>{services.length === 0 ? <p className="empty">The catalog is empty. Your first generated service will be registered atomically.</p> : <div className="catalog-table"><div className="table-head"><span>Component</span><span>Owner</span><span>Golden path</span><span>Lifecycle</span></div>{services.map((service) => <div className={service.id === artifact?.manifest.service_id ? 'table-row selected' : 'table-row'} key={service.id}><span><button className="service-link" onClick={() => inspect(service)} disabled={busy} aria-pressed={service.id === artifact?.manifest.service_id} aria-label={`Show artifact evidence for ${service.name}`}>{service.name}</button><small>{service.description}</small></span><span>{service.owner}</span><span>{service.template_id} · {service.template_version}</span><span className="lifecycle">{service.lifecycle}</span></div>)}</div>}</section>
    </main>
  )
}

export default App
