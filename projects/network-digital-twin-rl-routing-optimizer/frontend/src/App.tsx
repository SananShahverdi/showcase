import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { apiBase, errorMessage } from './portfolio'

type NodeMap=Record<string,{id:string;is_active:boolean}>
type Link={source:string;target:string;capacity:number;current_load:number;is_active:boolean}
type State={nodes:NodeMap;links:Link[];packets:{id:string;source:string;target:string;delivered:boolean;drop_reason?:string;path_taken:string[]}[]}
type Metric={algorithm:string;delivered_packets:number;dropped_packets:number;avg_latency_ms:number;p95_latency_ms:number;avg_link_utilization:number;energy_cost:number;policy_version?:string}
type Comparison={seed:number;num_packets:number;results:Record<string,Metric>}
type Training={policy_version:string;episodes:number;seed:number;final_mean_reward:number;checksum:string;reward_curve:number[]}
const API = apiBase(import.meta.env.VITE_API_URL ?? '/api')
async function request<T>(path:string,options?:RequestInit):Promise<T>{const response=await fetch(`${API}${path}`,options);const body=await response.json().catch(()=>({}));if(!response.ok)throw new Error(errorMessage(body.detail, response.status));return body as T}
const post=<T,>(path:string,body:unknown)=>request<T>(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
const ALGORITHMS=['dijkstra','ecmp','random','rl_agent']
// Mean reward per contiguous block of episodes, so the chart shows learning across the whole run.
function rewardBuckets(curve:number[],count=40){const size=Math.max(1,Math.ceil(curve.length/count));const buckets:number[]=[];for(let start=0;start<curve.length;start+=size){const block=curve.slice(start,start+size);buckets.push(block.reduce((sum,value)=>sum+value,0)/block.length)}return buckets}

function App(){
 const [state,setState]=useState<State>({nodes:{},links:[],packets:[]});const [training,setTraining]=useState<Training|null>(null);const [comparison,setComparison]=useState<Comparison|null>(null);const [topology,setTopology]=useState('mesh');const [nodes,setNodes]=useState(6);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('Build a topology, then train before evaluating RL_AGENT.')
 const refresh=()=>request<State>('/simulator/state').then(setState)
 useEffect(()=>{Promise.all([refresh(),request<{training:Training|null;comparison:Comparison|null}>('/lab/latest')]).then(([,latest])=>{if(!latest.training)return;setTraining(latest.training);setComparison(latest.comparison);setNotice(`Showing the current policy ${latest.training.policy_version}${latest.comparison?` and its comparison on seed ${latest.comparison.seed}`:''}. Retrain or rebuild to start a new experiment.`)}).catch((reason:Error)=>setError(reason.message))},[])
 const run=async(action:()=>Promise<void>,message:string)=>{setBusy(true);setError('');try{await action();await refresh();setNotice(message)}catch(reason){setError(reason instanceof Error?reason.message:'Unexpected error')}finally{setBusy(false)}}
 const build=()=>run(async()=>{await post('/simulator/topology',{topology,num_nodes:nodes});setTraining(null);setComparison(null)},`${topology} topology ready. Mutable runtime and policy state were reset.`)
 const train=()=>run(async()=>{setTraining(await post<Training>('/train',{episodes:500,seed:17}))},'A real tabular Q-learning policy was trained and checksummed.')
 const compare=()=>run(async()=>{setComparison(await post<Comparison>('/compare',{algorithms:ALGORITHMS,num_packets:80,seed:17}))},'All four algorithms replayed the same seeded traffic trace.')
 const seed=()=>run(async()=>{const result=await request<{training:Training;comparison:Comparison}>('/demo/seed',{method:'POST'});setTraining(result.training);setComparison(result.comparison)},'Seeded six-node lab trained and benchmarked on seed 17.')
 const replay=async()=>{if(training)setComparison(await post<Comparison>('/compare',{algorithms:ALGORITHMS,num_packets:comparison?.num_packets??80,seed:comparison?.seed??17}))}
 const fail=()=>run(async()=>{await post('/simulator/fail',{source:'n0',target:'n1'});await replay()},training?'Link n0 → n1 failed; comparison replayed against the active graph.':'Link n0 → n1 failed. Train a policy to compare routing around it.')
 const recover=()=>run(async()=>{await post('/simulator/recover',{source:'n0',target:'n1'});await replay()},training?'Link n0 → n1 recovered; comparison replayed against the restored graph.':'Link n0 → n1 recovered.')
 const failable=state.links.find(link=>link.source==='n0'&&link.target==='n1')
 const buckets=training?rewardBuckets(training.reward_curve):[]
 const low=Math.min(0,...buckets),high=Math.max(1,...buckets)
 const entries=comparison?Object.values(comparison.results):[]
 const positions=useMemo(()=>Object.keys(state.nodes).map((id,index)=>{const angle=(index/Object.keys(state.nodes).length)*Math.PI*2-Math.PI/2;return{id,x:50+38*Math.cos(angle),y:50+38*Math.sin(angle)}}),[state.nodes])
 const positionById=Object.fromEntries(positions.map(item=>[item.id,item]))
 return <div className="console">
  <aside><div className="logo">N<span>Δ</span></div><nav><a className="active" href="#lab">Lab</a><a href="#benchmark">Benchmark</a><a href="#replay">Replay</a></nav><div className="sim-label"><i></i><b>Simulation only</b><small>No live controller attached</small></div></aside>
  <main><header><div><p className="eyebrow">NETWORK DIGITAL TWIN / EXPERIMENT 017</p><h1>RouteLab <span>— decisions under pressure</span></h1></div><button className="accent" onClick={seed} disabled={busy}>Run complete demo</button></header>
   {error&&<div className="notice error" role="alert">{error}</div>}<div className="notice">{notice}</div>
   <section id="lab" className="labgrid">
    <div className="panel topology"><div className="panelhead"><div><p className="eyebrow">ACTIVE GRAPH</p><h2>Topology canvas</h2></div><span>{Object.keys(state.nodes).length} nodes · {state.links.filter(item=>item.is_active).length} links</span></div>
     <div className="graph" aria-label="Directed topology visualization">{state.links.filter(link=>link.is_active).map((link)=>{const a=positionById[link.source],b=positionById[link.target];if(!a||!b)return null;const dx=b.x-a.x,dy=b.y-a.y;return <i key={`${link.source}-${link.target}`} style={{left:`${a.x}%`,top:`${a.y}%`,width:`${Math.sqrt(dx*dx+dy*dy)}%`,transform:`rotate(${Math.atan2(dy,dx)*180/Math.PI}deg)`,opacity:.18+Math.min(link.current_load/link.capacity,.8)}} title={`${link.source} to ${link.target}: ${link.current_load}/${link.capacity}`}></i>})}{positions.map(node=><span key={node.id} className="node" style={{left:`${node.x}%`,top:`${node.y}%`}} title={`${node.id} active`}>{node.id}</span>)}{!positions.length&&<p>Build or seed a topology to populate the canvas.</p>}</div>
     <div className="controls"><label>Topology<select value={topology} onChange={event=>setTopology(event.target.value)}><option>mesh</option><option>ring</option><option>star</option></select></label><label>Nodes<input type="number" min="3" max="20" value={nodes} onChange={event=>setNodes(Number(event.target.value))}/></label><button onClick={build} disabled={busy||!Number.isInteger(nodes)||nodes<3||nodes>20}>Build & reset</button>{failable&&!failable.is_active?<button onClick={recover} disabled={busy}>Recover n0 → n1</button>:<button className="warn" onClick={fail} disabled={busy||!failable}>Fail n0 → n1</button>}</div>
    </div>
    <div className="panel training"><div className="panelhead"><div><p className="eyebrow">POLICY LAB</p><h2>Q-learning run</h2></div><span className={training?'ready':'waiting'}>{training?'trained':'untrained'}</span></div>
      <div className="formula">R = +100<small>delivery</small> − latency − 25<small>loop</small></div>
      <div className="trainingfacts"><div><span>Episodes</span><b>{training?.episodes??'—'}</b></div><div><span>Seed</span><b>{training?.seed??17}</b></div><div><span>Mean reward</span><b>{training?training.final_mean_reward.toFixed(1):'—'}</b></div></div>
      {training&&buckets.length?<figure className="curve-figure"><div className="curve" role="img" aria-label={`Mean episode reward rose from ${buckets[0].toFixed(1)} to ${buckets[buckets.length-1].toFixed(1)} over ${training.episodes} episodes`}>{buckets.map((value,index)=><i key={index} className={value<0?'negative':''} style={{height:`${Math.max(3,((value-low)/(high-low))*100)}%`}} title={`Episodes ${index*Math.ceil(training.reward_curve.length/40)+1}+: mean reward ${value.toFixed(1)}`}></i>)}</div><figcaption><span>episode 1</span><span>mean reward per {Math.ceil(training.reward_curve.length/40)} episodes</span><span>{training.episodes}</span></figcaption></figure>:<div className="curve"><p>Reward curve appears after training.</p></div>}
      {training&&<code>{training.policy_version} · sha256:{training.checksum.slice(0,16)}</code>}<button className="accent full" onClick={train} disabled={busy||!Object.keys(state.nodes).length}>Train 500 episodes</button>
    </div>
   </section>
   <section id="benchmark" className="panel benchmark"><div className="panelhead"><div><p className="eyebrow">FAIR REPLAY</p><h2>Baseline comparison</h2></div><div className="right"><span>{comparison?`${comparison.num_packets} packets · seed ${comparison.seed}`:'No run'}</span><button onClick={compare} disabled={busy||!training}>Compare identical trace</button></div></div>
    {!entries.length?<div className="empty">Train a policy, then compare it with Dijkstra, ECMP, and seeded random routing.</div>:<div className="table"><div className="row head"><span>Algorithm</span><span>Delivery</span><span>Avg latency</span><span>P95 latency</span><span>Avg utilization</span><span>Energy</span></div>{entries.map(metric=><div className={metric.algorithm==='rl_agent'?'row highlight':'row'} key={metric.algorithm}><b>{metric.algorithm.replace('_',' ')}</b><span>{metric.delivered_packets}/{comparison?.num_packets}</span><span>{metric.avg_latency_ms.toFixed(1)} ms</span><span>{metric.p95_latency_ms.toFixed(1)} ms</span><span>{(metric.avg_link_utilization*100).toFixed(1)}%</span><span>{metric.energy_cost.toFixed(0)}</span></div>)}</div>}
   </section>
   <section id="replay" className="replaygrid"><div className="panel"><div className="panelhead"><div><p className="eyebrow">PACKET TRACE</p><h2>Latest decisions</h2></div></div>{state.packets.slice(-5).reverse().map(packet=><div className="packet" key={packet.id}><i className={packet.delivered?'ok':'drop'}></i><b>{packet.source} → {packet.target}</b><span>{packet.path_taken.join(' · ')||packet.drop_reason}</span></div>)}{!state.packets.length&&<div className="empty">Evaluation packet paths appear here.</div>}</div><div className="panel boundary"><p className="eyebrow">CLAIM BOUNDARY</p><h2>Evidence, not deployment</h2><p>This console models capacity, utilization delay, queues, loss, and directed failures. It does not change a physical network. Promotion to a real controller requires separate safety and integration review.</p></div></section>
  </main>
 </div>
}
export default App
