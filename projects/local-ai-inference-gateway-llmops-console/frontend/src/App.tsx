import { useEffect, useRef, useState } from 'react'
import './App.css'
import { projectRoot, errorMessage } from './portfolio'

type Provider={id:string;name:string;type:string;is_active:boolean;priority:number;privacy_level:string;health_status:string;capabilities:string[];model_name?:string}
type Metrics={total_requests:number;total_errors:number;provider_attempts:number;fallback_requests:number;avg_latency_ms:number;total_tokens:number;total_cost:number}
type Log={id:string;request_id:string;model_name:string;latency_ms:number;error:boolean;error_class?:string;attempt:number;fallback:boolean;capability:string;total_tokens:number;timestamp:string}
type Template={id:string;name:string;active_version_id:string;versions:{id:string;version_number:number;template_string:string;variables:string[]}[]}
type IssuedKey={key:string;name:string;scopes:string[];token_quota:number}
type ChatResult={choices:{message:{content:string}}[];provider:string;fallback:boolean;usage:{total_tokens:number}}
const SAMPLE_PROMPT='Summarize this release note for an engineering lead. Contact: owner@example.com'
// The offline provider answers in well under a millisecond; keep that visible instead of rounding to 0.0.
const ms=(value:number)=>value<1?value.toFixed(2):value.toFixed(1)
// The browser-session key is a small scoped demo key for this loopback console; it lives only in this tab's sessionStorage.
const SESSION_KEY='inference-gateway-session-key'
const readSessionKey=():IssuedKey|null=>{try{const raw=sessionStorage.getItem(SESSION_KEY);return raw?JSON.parse(raw) as IssuedKey:null}catch{return null}}
const storeSessionKey=(key:IssuedKey)=>{try{sessionStorage.setItem(SESSION_KEY,JSON.stringify(key))}catch{/* storage unavailable: the key stays in memory */}}
const emptyMetrics:Metrics={total_requests:0,total_errors:0,provider_attempts:0,fallback_requests:0,avg_latency_ms:0,total_tokens:0,total_cost:0}
async function request<T>(path:string,options?:RequestInit):Promise<T>{const response=await fetch(`${projectRoot}${path}`,options);const body=await response.json().catch(()=>({}));if(!response.ok)throw new Error(errorMessage(body.detail, response.status));return body as T}

function App(){
 const [providers,setProviders]=useState<Provider[]>([]);const [metrics,setMetrics]=useState(emptyMetrics);const [logs,setLogs]=useState<Log[]>([]);const [templates,setTemplates]=useState<Template[]>([]);const [gatewayKey,setGatewayKey]=useState<IssuedKey|null>(null);const [prompt,setPrompt]=useState(SAMPLE_PROMPT);const started=useRef(false);const [response,setResponse]=useState('');const [route,setRoute]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('Seed a local provider and scoped key to exercise the complete gateway.')
 const refresh=async()=>{const [p,m,l,t]=await Promise.all([request<Provider[]>('/api/admin/providers'),request<Metrics>('/api/admin/metrics'),request<Log[]>('/api/admin/logs'),request<Template[]>('/api/admin/templates')]);setProviders(p);setMetrics(m);setLogs(l);setTemplates(t);return p}
 const run=async(action:()=>Promise<void>,message:string)=>{setBusy(true);setError('');try{await action();await refresh();setNotice(message)}catch(reason){setError(reason instanceof Error?reason.message:'Unexpected error')}finally{setBusy(false)}}
 const sendChat=async(key:IssuedKey,text:string)=>{const result=await request<ChatResult>('/v1/chat/completions',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${key.key}`},body:JSON.stringify({model:'default',messages:[{role:'user',content:text}],requires_high_privacy:true,redact_pii:true})});setResponse(result.choices[0].message.content);setRoute(`${result.provider}${result.fallback?' · fallback':''} · ${result.usage.total_tokens} tokens`)}
 useEffect(()=>{
  if(started.current)return
  started.current=true
  // When the gateway already has an active provider, issue a small scoped key for this browser
  // session (kept in this tab's sessionStorage and reused across reloads) and send the sample prompt, so the playground opens
  // with a real routed, redacted response instead of an empty panel.
  const warmUp=async()=>{const available=await refresh();if(!available.some(provider=>provider.is_active))return
   setBusy(true);try{const issue=async()=>{const fresh=await request<IssuedKey>('/api/admin/keys',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'browser-session',scopes:['chat','embeddings'],requests_per_minute:30,token_quota:5000})});storeSessionKey(fresh);return fresh}
   // Reuse this tab's key across reloads; issue a new one only if there is none or the gateway no longer accepts it.
   let issued=readSessionKey()??await issue();try{await sendChat(issued,SAMPLE_PROMPT)}catch{issued=await issue();await sendChat(issued,SAMPLE_PROMPT)}setGatewayKey(issued);await refresh();setNotice('Issued a scoped key for this browser session and sent the sample prompt through the gateway. Edit the prompt and send again.')}finally{setBusy(false)}}
  warmUp().catch((reason:Error)=>setError(reason.message))
 },[])
 const seed=()=>run(async()=>{const result=await request<{api_key:IssuedKey}>('/api/demo/seed',{method:'POST'});setGatewayKey(result.api_key);setResponse('');setRoute('')},'Local demo provider, prompt version, quota, and one-time API key are ready.')
 const chat=()=>run(()=>sendChat(gatewayKey as IssuedKey,prompt),'Private chat completed; redaction, route, usage, and attempt were recorded.')
 const embed=()=>run(async()=>{const result=await request<{data:{embedding:number[]}[];provider:string;usage:{total_tokens:number}}>('/v1/embeddings',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${gatewayKey?.key}`},body:JSON.stringify({input:prompt,requires_high_privacy:true,redact_pii:true})});setResponse(`[${result.data[0].embedding.slice(0,8).join(', ')} …]`);setRoute(`${result.provider} · ${result.usage.total_tokens} tokens · deterministic embedding`)},'Embedding normalized to the OpenAI-compatible response contract.')
 const probe=(id:string)=>run(()=>request(`/api/admin/providers/${id}/probe`,{method:'POST'}),'Provider health probe completed and status updated.')
 const success=metrics.total_requests?Math.round((1-metrics.total_errors/Math.max(metrics.provider_attempts,1))*100):100
 return <div className="gateway">
  <aside><div className="mark">λ<span>/</span></div><nav><a className="active" href="#overview">Overview</a><a href="#playground">Playground</a><a href="#providers">Providers</a><a href="#prompts">Prompts</a><a href="#logs">Request logs</a></nav><div className="privacy"><span>LOCAL-FIRST</span><b>Privacy policy active</b><small>Fallback cannot downgrade</small></div></aside>
  <main><header><div><p className="kicker">LLM OPERATIONS / LOCAL ENVIRONMENT</p><h1>Inference gateway</h1><p>One contract. Explainable routing. No silent privacy downgrade.</p></div><button className="primary" onClick={seed} disabled={busy}>Seed secure demo</button></header>
   {error&&<div className="notice error" role="alert">{error}</div>}<div className="notice">{notice}</div>
   <section id="overview" className="cards"><article><span>Requests</span><b>{metrics.total_requests}</b><small>{metrics.provider_attempts} provider attempts</small></article><article><span>Success rate</span><b>{success}%</b><small>{metrics.total_errors} failed attempts</small></article><article><span>Average latency</span><b>{ms(metrics.avg_latency_ms)}<em> ms</em></b><small>Gateway + provider</small></article><article><span>Token ledger</span><b>{metrics.total_tokens}</b><small>${metrics.total_cost.toFixed(4)} estimated</small></article><article><span>Fallbacks</span><b>{metrics.fallback_requests}</b><small>Policy-safe only</small></article></section>
   <section className="layout">
    <div id="playground" className="panel playground"><div className="panelhead"><div><p className="kicker">OPENAI-COMPATIBLE CLIENT</p><h2>Private playground</h2></div><span className="policy">HIGH PRIVACY</span></div>
      {!gatewayKey&&<div className="key-empty">No gateway key in this browser session. Seed the demo to create a provider and a scoped key; the raw key is held in memory only.</div>}{gatewayKey&&<div className="key"><span>Scoped key · {gatewayKey.name}</span><code>{gatewayKey.key.slice(0,12)}••••••••••••</code><small>{gatewayKey.scopes.join(' · ')} · {gatewayKey.token_quota.toLocaleString('en-US')} token quota</small></div>}
      <label>Prompt<textarea maxLength={100000} value={prompt} onChange={event=>setPrompt(event.target.value)} rows={7}/></label><div className="toggles"><span>✓ Local providers only</span><span>✓ PII redaction</span><span>✓ Attempt logging</span></div><div className="actions"><button className="primary" onClick={chat} disabled={busy||!gatewayKey}>Send chat</button><button onClick={embed} disabled={busy||!gatewayKey}>Create embedding</button></div>
      <div className="response"><div><span>Normalized response</span><small>{route||'Awaiting request'}</small></div><pre>{response||'The response body and route evidence will appear here.'}</pre></div>
    </div>
    <div id="providers" className="panel providers"><div className="panelhead"><div><p className="kicker">ROUTING POOL</p><h2>Provider health</h2></div><span>{providers.length} configured</span></div>{providers.length===0?<div className="empty">No providers. Seed the deterministic local profile.</div>:providers.map(provider=><article key={provider.id}><div className={`provider-icon ${provider.type}`}>{provider.type.slice(0,2).toUpperCase()}</div><div><b>{provider.name}</b><small>{provider.capabilities.join(' · ')} · P{provider.priority} · {provider.privacy_level}</small></div><span className={`health ${provider.health_status}`}>{provider.health_status}</span><button onClick={()=>probe(provider.id)} disabled={busy}>Probe</button></article>)}</div>
   </section>
   <section className="lower">
    <div id="prompts" className="panel"><div className="panelhead"><div><p className="kicker">IMMUTABLE REGISTRY</p><h2>Prompt versions</h2></div><span>{templates.length} template{templates.length===1?'':'s'}</span></div>{templates.length===0?<div className="empty">Seed a strict, versioned template.</div>:templates.map(template=>{const active=template.versions.find(version=>version.id===template.active_version_id);return <article className="template" key={template.id}><div><b>{template.name}</b><small>{template.versions.length} version{template.versions.length===1?'':'s'} · active v{active?.version_number??'—'}</small></div><code>{active?.template_string}</code><span>{(active?.variables??[]).map(variable=>`{${variable}}`).join(' ')}</span></article>})}</div>
    <div id="logs" className="panel"><div className="panelhead"><div><p className="kicker">ATTEMPT-LEVEL EVIDENCE</p><h2>Request log</h2></div><span>Metadata only</span></div>{logs.length===0?<div className="empty">Provider attempts appear here; prompts and keys do not.</div>:<div className="logtable"><div className="logrow head"><span>Request</span><span>Capability</span><span>Attempt</span><span>Latency</span><span>Status</span></div>{logs.slice(0,7).map(log=><div className="logrow" key={log.id}><code>{log.request_id.slice(-8)}</code><span>{log.capability}</span><span>#{log.attempt}{log.fallback?' fallback':''}</span><span>{ms(log.latency_ms)} ms</span><b className={log.error?'bad':'good'}>{log.error?log.error_class:'ok'}</b></div>)}</div>}</div>
   </section><footer><span>Raw prompts disabled in logs</span><span>Gateway key kept in this tab only</span><span>OpenAI-compatible /v1 contract</span></footer>
  </main>
 </div>
}
export default App
