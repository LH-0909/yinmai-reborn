import type {GraphData,GraphNode} from './types'

export interface Position3 {x:number;y:number;z:number}
export const neuralColors:Record<string,string>={resource:'#39c7ff',seal_object:'#7cbaa0',seal_draft:'#53e2ff',character:'#83b9ff',script:'#b38aff',seal_type:'#ffc76b',collection:'#ff80c5',document:'#5ae6bc',person:'#f3a76b',period:'#a69aff',place:'#6ee2d1'}
function unit(id:string,offset=0){let h=2166136261;for(const c of id+offset)h=Math.imul(h^c.charCodeAt(0),16777619);return (h>>>0)/4294967296}

export function graphScope(data:GraphData,center:string,depth:number,path:string[]=[]){
 const root=data.nodes.some(n=>n.id===center)?center:data.nodes.find(n=>(n.kind==='seal_draft'||n.kind==='seal_object'))?.id||data.nodes[0]?.id||''
 const adjacent=new Map(data.nodes.map(n=>[n.id,[] as string[]]))
 for(const e of data.edges){adjacent.get(e.source)?.push(e.target);adjacent.get(e.target)?.push(e.source)}
 const distances=new Map<string,number>(root?[[root,0]]:[]),queue=root?[root]:[]
 for(let i=0;i<queue.length;i++)for(const id of adjacent.get(queue[i])||[])if(!distances.has(id)){distances.set(id,distances.get(queue[i])!+1);queue.push(id)}
 const pathSet=new Set(path),nodes=data.nodes.filter(n=>depth===0||distances.has(n.id)&&distances.get(n.id)!<=depth||pathSet.has(n.id))
 const ids=new Set(nodes.map(n=>n.id)),edges=data.edges.filter(e=>ids.has(e.source)&&ids.has(e.target))
 return {root,nodes,edges,distances}
}

/** Deterministic spatial layout: actual claims supply springs, type bands supply
 * visual grouping only. Coordinates never encode confidence or chronology. */
export function neuralPositions(nodes:GraphNode[],edges:GraphData['edges']):Map<string,Position3>{
 const positions=new Map<string,Position3>(),kinds=[...new Set(nodes.map(n=>n.kind))]
 const bands:Record<string,number>={resource:105,seal_object:38,seal_draft:38,script:5,seal_type:0,collection:-5,character:-85,document:105,person:50,period:20,place:-30}
 const groups=new Map(kinds.map(k=>[k,nodes.filter(n=>n.kind===k).sort((a,b)=>a.id.localeCompare(b.id))]))
 for(const [kind,group] of groups)group.forEach((n,i)=>{
  const a=i*2.399963229728653+unit(kind)*6.28,r=(kind==='character'?115:kind==='seal_draft'?100:60)*Math.sqrt((i+.7)/group.length)
  positions.set(n.id,{x:Math.cos(a)*r,y:(bands[kind]||0)+(unit(n.id,1)-.5)*35,z:Math.sin(a)*r+(unit(n.id,2)-.5)*30})
 })
 if(nodes.length<2)return positions
 const indexed=new Map(nodes.map((n,i)=>[n.id,i])),ps=nodes.map(n=>positions.get(n.id)!),targets=ps.map(p=>({...p}))
 const links=edges.filter(e=>indexed.has(e.source)&&indexed.has(e.target)).map(e=>[indexed.get(e.source)!,indexed.get(e.target)!])
 // Bounded work even at the API's 500-node cap. All data remains visible.
 for(let step=0;step<(nodes.length>180?45:95);step++){
  const f=ps.map(()=>({x:0,y:0,z:0}))
  for(let i=0;i<ps.length;i++)for(let j=i+1;j<ps.length;j++){
   const a=ps[i],b=ps[j],dx=a.x-b.x,dy=a.y-b.y,dz=a.z-b.z,ds=dx*dx+dy*dy+dz*dz+8,s=185/(ds*Math.sqrt(ds))
   const x=dx*s,y=dy*s,z=dz*s;f[i].x+=x;f[i].y+=y;f[i].z+=z;f[j].x-=x;f[j].y-=y;f[j].z-=z
  }
  for(const [i,j] of links){const a=ps[i],b=ps[j],dx=b.x-a.x,dy=b.y-a.y,dz=b.z-a.z,d=Math.sqrt(dx*dx+dy*dy+dz*dz)||1,s=(d-67)/d*.012;f[i].x+=dx*s;f[i].y+=dy*s;f[i].z+=dz*s;f[j].x-=dx*s;f[j].y-=dy*s;f[j].z-=dz*s}
  for(let i=0;i<ps.length;i++){const a=ps[i],t=targets[i];a.x+=Math.max(-3,Math.min(3,f[i].x+(t.x-a.x)*.035));a.y+=Math.max(-3,Math.min(3,f[i].y+(t.y-a.y)*.075));a.z+=Math.max(-3,Math.min(3,f[i].z+(t.z-a.z)*.035))}
 }
 return positions
}

export function flowAssignments(edges:GraphData['edges'],budget=900){
 edges=edges.filter(e=>e.status==='page_asserted'||e.status==='human_reviewed')
 if(!edges.length)return []
 if(edges.length>budget)return Array.from({length:budget},(_,i)=>{const e=edges[Math.floor(i*edges.length/budget)];return {edgeId:e.id,phase:unit(e.id),speed:.10+unit(e.id,3)*.08}})
 const perEdge=Math.max(1,Math.min(6,Math.floor(budget/edges.length)))
 return edges.flatMap(e=>Array.from({length:perEdge},(_,i)=>({edgeId:e.id,phase:(i+unit(e.id))/perEdge,speed:.10+unit(e.id,3)*.08})))
}

/** Respect depth when picking; only a near tie favours an easier node target. */
export function nearestGraphHit<T extends {distance:number;object:{userData:{type?:string}}}>(hits:T[]):T|null{
 const first=hits[0]
 if(!first)return null
 return hits.find(h=>h.object.userData.type==='node'&&h.distance<=first.distance+.5)||first
}
