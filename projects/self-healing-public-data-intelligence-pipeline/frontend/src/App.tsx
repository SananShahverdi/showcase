import { useEffect, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

type Dashboard = { source_health: { total_tracked:number; active:number; degraded:number }; extraction_trends:{ total_extracted:number; valid_records:number; quarantined_records:number; success_rate:number; drifted_runs:number }; repair_queue:{ open_failures:number; pending_proposals:number } }
type Source = { id:string; name:string; url:string; status:string }
type Recipe = { id:string; source_id:string; version:number; is_active:boolean; success_rate:number }
type Run = { id:string; source_id:string; timestamp:string; extracted_count:number; valid_count:number; schema_drift:boolean }
type Failure = { id:string; field:string; error_message:string; timestamp:string }
type Proposal = { id:string; target_field:string; proposed_selectors:Record<string,string>; rationale:string; confidence_score:number; replay_passed:boolean; approved:boolean }

const API = apiBase(import.meta.env.VITE_API_URL ?? '/api')
async function request<T>(path:string, options?:RequestInit):Promise<T>{ const response=await fetch(`${API}${path}`,options); const body=await response.json().catch(()=>({})); if(!response.ok) throw new Error(errorMessage(body.detail, response.status)); return body as T }
const emptyDashboard:Dashboard={source_health:{total_tracked:0,active:0,degraded:0},extraction_trends:{total_extracted:0,valid_records:0,quarantined_records:0,success_rate:1,drifted_runs:0},repair_queue:{open_failures:0,pending_proposals:0}}

function App(){
  const [dashboard,setDashboard]=useState(emptyDashboard)
  const [sources,setSources]=useState<Source[]>([])
  const [failures,setFailures]=useState<Failure[]>([])
  const [proposals,setProposals]=useState<Proposal[]>([])
  const [recipes,setRecipes]=useState<Recipe[]>([])
  const [runs,setRuns]=useState<Run[]>([])
  const [loaded,setLoaded]=useState(false)
  const [busy,setBusy]=useState(false); const [error,setError]=useState(''); const [notice,setNotice]=useState('')
  const refresh=async()=>{ const [d,s,f,p,r,u]=await Promise.all([request<Dashboard>('/dashboard'),request<Source[]>('/sources'),request<Failure[]>('/failures'),request<Proposal[]>('/repair/proposals'),request<Recipe[]>('/recipes'),request<Run[]>('/runs')]);setDashboard(d);setSources(s);setFailures(f);setProposals(p);setRecipes(r);setRuns(u);setLoaded(true) }
  useEffect(()=>{refresh().catch((reason:Error)=>setError(reason.message))},[])
  const run=async(action:()=>Promise<unknown>,message:string)=>{setBusy(true);setError('');try{await action();await refresh();setNotice(message)}catch(reason){setError(reason instanceof Error?reason.message:'Unexpected error')}finally{setBusy(false)}}
  const seed=()=>run(()=>request('/demo/seed',{method:'POST'}),'Fixture captured: one valid record published and one quarantined.')
  const propose=(id:string)=>run(()=>request(`/repair/propose/${id}`,{method:'POST'}),'An explainable selector proposal is ready for replay.')
  const replay=(id:string)=>run(()=>request(`/repair/replay/${id}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({test_html:"<main><article class='product'><h2>Pears</h2><span data-field='price'>3.10</span></article></main>"})}),'Replay passed against typed fixture data; activation is now eligible.')
  const activate=(id:string)=>run(()=>request(`/repair/activate/${id}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({approved:true})}),'Recipe version 2 activated with human approval.')
  const extracted=dashboard.extraction_trends.total_extracted
  const success=extracted?Math.round(dashboard.extraction_trends.success_rate*100):null
  // A source is degraded when its active recipe's latest run quarantined records.
  const sourceStatus=(source:Source)=>recipes.some((recipe)=>recipe.source_id===source.id&&recipe.is_active&&recipe.success_rate<1)?'degraded':source.status
  const activeVersion=(source:Source)=>recipes.find((recipe)=>recipe.source_id===source.id&&recipe.is_active)?.version
  const runsFor=(source:Source)=>runs.filter((run)=>run.source_id===source.id).sort((a,b)=>a.timestamp.localeCompare(b.timestamp)).slice(-8)
  const hint=loaded&&sources.length===0?'Load the fixture fleet to inspect a real quality gate.':''
  return <div className="app">
    <header><div className="brand"><span>∿</span><div><b>Sourcewell</b><small>PUBLIC DATA CONTROL PLANE</small></div></div><nav><button onClick={()=>document.getElementById('fleet')?.scrollIntoView({behavior:'smooth'})}>Fleet</button><button onClick={()=>document.getElementById('quality')?.scrollIntoView({behavior:'smooth'})}>Quality</button><button onClick={()=>document.getElementById('repairs')?.scrollIntoView({behavior:'smooth'})}>Repairs</button></nav><button className="primary" onClick={seed} disabled={busy}>Load fixture fleet</button></header>
    <main>
      <section className="hero"><div><p className="kicker">OPERATIONS / SOURCE FLEET</p><h1>Trust the data,<br/>especially when the page changes.</h1><p>Captured HTML is extracted server-side, validated at the boundary, and repaired only after replay and approval.</p></div><div className="health"><span className={dashboard.source_health.degraded?'pulse warn':'pulse'} aria-hidden="true"></span><div><b>{dashboard.source_health.degraded?'Attention required':sources.length?'Fleet ready':'No sources yet'}</b><small>{dashboard.source_health.active} active · {dashboard.source_health.degraded} degraded</small></div></div></section>
      {error&&<div className="notice error" role="alert">{error}</div>}<div className="notice-slot" aria-live="polite">{(notice||hint)&&<div className="notice">{notice||hint}</div>}</div>
      <section className="metrics"><article><span>Extraction quality</span><b>{success===null?'—':`${success}%`}</b><div><i style={{width:`${success??0}%`}}></i></div><small>{dashboard.extraction_trends.valid_records} published / {dashboard.extraction_trends.total_extracted} extracted</small></article><article><span>Quarantine</span><b>{dashboard.extraction_trends.quarantined_records}</b><small>Blocked from analytics</small></article><article><span>DOM drift</span><b>{dashboard.extraction_trends.drifted_runs}</b><small>Structural changes detected</small></article><article><span>Repair queue</span><b>{dashboard.repair_queue.pending_proposals}</b><small>{dashboard.repair_queue.open_failures} field failures</small></article></section>
      <section className="grid">
        <div className="panel fleet" id="fleet"><div className="title"><div><p className="kicker">SOURCE HEALTH</p><h2>Tracked fleet</h2></div><span>{sources.length} sources</span></div>{sources.length===0?<div className="empty">No sources registered. Load the offline fixture.</div>:sources.map((source,index)=><article key={source.id}><div className="source-icon">{index+1}</div><div><b>{source.name}</b><small>{source.url}</small></div><span className={sourceStatus(source)==='active'?'badge':'badge warn'}>{sourceStatus(source)}{activeVersion(source)?` · v${activeVersion(source)}`:''}</span><div className="run-history"><div className="spark" role="img" aria-label={`Published share of extracted records over the last ${runsFor(source).length} run(s)`}>{runsFor(source).map((run)=><i key={run.id} title={`${new Date(run.timestamp).toLocaleString()}: ${run.valid_count}/${run.extracted_count} published${run.schema_drift?' · DOM drift':''}`} className={run.valid_count<run.extracted_count?'partial':''} style={{height:`${Math.max(12,run.extracted_count?run.valid_count/run.extracted_count*100:0)}%`}}/>)}</div>{runsFor(source).length>0&&<small>latest {runsFor(source).at(-1)!.valid_count}/{runsFor(source).at(-1)!.extracted_count} published</small>}</div></article>)}</div>
        <div className="panel quarantine" id="quality"><div className="title"><div><p className="kicker">QUALITY GATE</p><h2>Quarantine workbench</h2></div><span>{failures.length} failures</span></div>{failures.length===0?<div className="empty">Invalid records and selector misses appear here with field-level reasons.</div>:failures.map((failure)=><article key={failure.id}><div><span className="field">{failure.field||'record'}</span><b>{failure.error_message}</b><small>{new Date(failure.timestamp).toLocaleString()} · analytics blocked</small></div><button onClick={()=>propose(failure.id)} disabled={busy||proposals.some((item)=>item.target_field===failure.field)}>Propose repair</button></article>)}</div>
      </section>
      <section className="panel repairs" id="repairs"><div className="title"><div><p className="kicker">REPLAY-GATED CHANGE</p><h2>Repair review</h2></div><span>Human approval required</span></div>{proposals.length===0?<div className="empty wide">Choose a quarantined failure to create a deterministic, explainable locator candidate.</div>:proposals.map((proposal)=><div className="proposal" key={proposal.id}><div className="confidence"><b>{Math.round(proposal.confidence_score*100)}</b><small>confidence</small></div><div className="proposal-copy"><span className="field">{proposal.target_field}</span><h3>{proposal.proposed_selectors[proposal.target_field]}</h3><p>{proposal.rationale}</p><div className="steps"><span className="done">1 · Candidate</span><span className={proposal.replay_passed?'done':''}>2 · Fixture replay</span><span className={proposal.approved?'done':''}>3 · Activate v2</span></div></div><div className="proposal-actions"><button onClick={()=>replay(proposal.id)} disabled={busy||proposal.replay_passed}>Run replay</button><button className="primary" onClick={()=>activate(proposal.id)} disabled={busy||!proposal.replay_passed||proposal.approved}>{proposal.approved?'Activated':'Approve & activate'}</button></div></div>)}</section>
      <footer><span>Offline fixture mode · no network requests</span><span>Invalid records never enter analytics</span></footer>
    </main>
  </div>
}
export default App
