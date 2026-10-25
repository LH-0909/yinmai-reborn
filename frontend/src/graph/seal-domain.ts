import type {GraphData,GraphNode,GraphEdge} from './types'
import type {Position3} from './neural-layout'

export interface SealPreview {node_id:string;label:string;page_url:string;display_url:string;image_url:string;width:number;height:number}
export type PreviewRegistry=Record<string,SealPreview>
export const isAsserted=(edge:GraphEdge)=>edge.status==='page_asserted'||edge.status==='human_reviewed'
export const isSeal=(node:GraphNode)=>node.kind==='seal_draft'||node.kind==='seal_object'
export interface MuseumRecord extends SealPreview {
 official_title:string;accession_number:string;museum:string;source_id?:string;catalogue_record_id?:string;identifier_label?:string;document_id:string;page_sha256:string;status?:string;period:string;period_index?:string;period_body?:string;period_conflict?:boolean;material:string;dimensions:string;transcription:string;transcription_scope:string;caption:string;script:string;maker?:string;source_excerpt?:string;source_excerpt_truncated?:boolean;image_match_basis?:string;caption_note?:string;interpretation_note?:string;field_provenance?:{period_and_maker?:{index_url:string}};
 impression?:{display_url:string;image_url:string;width:number;height:number;caption:string}
}
export type MuseumRegistry=Record<string,MuseumRecord>
const museumAuthorities:Record<string,{museum:string;page:RegExp;image:RegExp}>={
 dpm:{museum:'故宫博物院',page:/^https:\/\/www\.dpm\.org\.cn\/collection\/seal\/\d+\.html$/,image:/^https:\/\/img\.dpm\.org\.cn\/Uploads\/(?:Picture|image|File)\//},
 nmc:{museum:'中国国家博物馆',page:/^https:\/\/www\.chnmuseum\.cn\/zp\/zpml\/[^/]+\/\d{6}\/t\d+_\d+\.shtml$/,image:/^https:\/\/www\.chnmuseum\.cn\/zp\/zpml\//},
 nyw:{museum:'南越王博物院',page:/^https:\/\/www\.nywmuseum\.org\.cn\/Collection\/Details\/(?:dcjp)?\?nid=\d+$/,image:/^https:\/\/file\.nywmuseum\.org\.cn\/nyw-museum\//}
}
function verifiedCaption(row:MuseumRecord){
 if(row.caption===row.official_title)return true
 const named=(s:string)=>[...s.matchAll(/“([^”]+)”/g)].map(m=>m[1])
 const a=named(row.official_title),b=named(row.caption)
 return row.image_match_basis==='official_object_gallery_same_complete_named_inscription'&&a.length===1&&b.length===1&&a[0]===b[0]&&a[0]===row.transcription&&!/钤本|印面|背面|局部|边款/.test(row.caption)
}
/** A public draft image is not proof that a historical physical seal exists.
 * Only curated official object/page/accession receipts can enter this gallery.
 * Manual claims and copied attributes alone never grant museum-record status. */
export function museumRecordFor(node:GraphNode|undefined,data:GraphData,registry:MuseumRegistry){
 if(!node||node.kind!=='seal_object')return undefined
 const item=registry[node.id],doc=item&&data.documents.find(d=>d.id===item.document_id)
 const source=item?.source_id||'dpm',authority=museumAuthorities[source]
 if(!item||!authority||authority.museum!==item.museum||!authority.page.test(item.page_url)||node.attributes.record_type!=='museum_object'||node.label!==item.label||node.attributes.url!==item.page_url||node.attributes.accession_number!==item.accession_number)return undefined
 if(['official_title','transcription','museum','period','material','dimensions'].some(key=>node.attributes[key]!==item[key as keyof MuseumRecord]))return undefined
 if(source==='dpm'&&!/^(故|新)\d{8}(?:[-－]\d+(?:\/\d+)?)?$/.test(item.accession_number))return undefined
 if(source!=='dpm'&&(!item.catalogue_record_id||node.attributes.catalogue_record_id!==item.catalogue_record_id||!(source==='nmc'?item.page_url.endsWith('_'+item.catalogue_record_id+'.shtml'):item.page_url.endsWith('nid='+item.catalogue_record_id))))return undefined
 if(item.status==='unavailable'){if(item.display_url||item.width||item.height)return undefined}
 else if(!previewFor(node,registry)||!verifiedCaption(item)||!authority.image.test(item.image_url))return undefined
 const impression=item.impression
 if(impression&&(impression.display_url!==`/assets/seal-previews/${node.id}-impression.webp`||![item.official_title+'钤本',item.caption+'钤本'].includes(impression.caption)||!authority.image.test(impression.image_url)||![impression.width,impression.height].every(n=>Number.isFinite(n)&&n>0)))return undefined
 return doc&&doc.source_id===source&&doc.url===item.page_url&&doc.sha256===item.page_sha256&&/^[a-f0-9]{64}$/.test(item.page_sha256)&&!!doc.fetched_at&&doc.method==='public_html_metadata_extraction'&&data.edges.some(e=>isAsserted(e)&&e.source===node.id&&e.predicate==='recorded_in'&&e.document_id===doc.id&&e.attributes.accession_number===item.accession_number&&(!item.catalogue_record_id||e.attributes.catalogue_record_id===item.catalogue_record_id)&&data.nodes.some(n=>n.id===e.target&&n.kind==='resource'&&n.attributes.source_id===source))?item:undefined
}
export function museumReadingData(data:GraphData,registry:MuseumRegistry):GraphData{
 const objects=new Set(data.nodes.filter(n=>museumRecordFor(n,data,registry)).map(n=>n.id))
 const edges=data.edges.filter(e=>objects.has(e.source)&&isAsserted(e)&&registry[e.source]?.document_id===e.document_id)
 const keep=new Set([...objects,...edges.map(e=>e.target)]),nodes=data.nodes.filter(n=>keep.has(n.id))
 return {...data,nodes,edges}
}

export function previewFor(node:GraphNode|undefined,registry:PreviewRegistry){
 if(!node||!isSeal(node))return undefined
 const item=registry[node.id]
 return item&&/^node-[a-f0-9]{28}$/.test(node.id)&&item.node_id===node.id&&item.label===node.label&&item.page_url===node.attributes.url&&item.display_url===`/assets/seal-previews/${node.id}.webp`&&Number.isFinite(item.width)&&item.width>0&&Number.isFinite(item.height)&&item.height>0?item:undefined
}
export function sealCharacters(data:GraphData,id:string){
 const rows=data.edges.filter(e=>isAsserted(e)&&e.source===id&&e.predicate==='contains_character').flatMap(e=>{
  const node=data.nodes.find(n=>n.id===e.target&&n.kind==='character')
  const positions=Array.isArray(e.attributes.positions)?e.attributes.positions.filter((p:unknown)=>typeof p==='number'&&Number.isFinite(p)&&p>=1):[]
  return node?[{node,edge:e,evidenceEdges:[e],position:Math.min(...positions,999)}]:[]
 })
 const grouped=new Map<string,typeof rows[number]>()
 for(const row of rows){const old=grouped.get(row.node.id);if(old){old.position=Math.min(old.position,row.position);if(!old.evidenceEdges.some(e=>e.id===row.edge.id))old.evidenceEdges.push(row.edge)}else grouped.set(row.node.id,row)}
 return [...grouped.values()].sort((a,b)=>a.position-b.position||a.node.label.localeCompare(b.node.label,'zh'))
}
export function relatedSeals(data:GraphData,id:string,character=''){
 const chars=new Set(sealCharacters(data,id).map(r=>r.node.id).filter(x=>!character||x===character))
 const anchorKind=data.nodes.find(n=>n.id===id)?.kind
 return data.nodes.filter(n=>isSeal(n)&&n.kind===anchorKind&&n.matched!==false&&n.id!==id).map(node=>{
  const shared=sealCharacters(data,node.id).filter(r=>chars.has(r.node.id))
  return {node,shared}
 }).filter(r=>r.shared.length).sort((a,b)=>b.shared.length-a.shared.length||a.node.label.localeCompare(b.node.label,'zh'))
}
/** Display scope is made only from actual contains_character claims.
 * Shared text is a browsing aid, never a style/author/chronology assertion. */
export function sealContext(data:GraphData,anchor:string,lens:'read'|'related',character='',registry:PreviewRegistry={},relatedLimit=Infinity){
 const root=data.nodes.find(n=>n.id===anchor&&isSeal(n)&&n.matched!==false)
 if(!root)return {...data,nodes:[],edges:[]}
 const chars=sealCharacters(data,anchor).filter(r=>!character||r.node.id===character)
 const ids=new Set([anchor,...chars.map(r=>r.node.id),...(lens==='related'?relatedSeals(data,anchor,character).slice(0,Math.max(0,relatedLimit)).map(r=>r.node.id):[])])
 const nodes=data.nodes.filter(n=>ids.has(n.id)).map(n=>{const p=previewFor(n,registry);return {...n,attributes:{...n.attributes,display_preview:p?.display_url,preview_width:p?.width,preview_height:p?.height}}})
 const grouped=new Map<string,GraphEdge>()
 for(const e of data.edges.filter(e=>isAsserted(e)&&e.predicate==='contains_character'&&ids.has(e.source)&&ids.has(e.target))){const key=e.source+'|'+e.target+'|'+e.predicate,old=grouped.get(key);if(old){if(!old.attributes.evidence_edge_ids.includes(e.id))old.attributes.evidence_edge_ids.push(e.id);if(!old.attributes.evidence_document_ids.includes(e.document_id))old.attributes.evidence_document_ids.push(e.document_id)}else grouped.set(key,{...e,attributes:{...e.attributes,evidence_edge_ids:[e.id],evidence_document_ids:[e.document_id]}})}
 const edges=[...grouped.values()]
 return {...data,nodes,edges}
}
/** Concentric reading distance is visual organization, not historical hierarchy. */
export function sealOrbitPositions(nodes:GraphNode[],anchor:string):Map<string,Position3>{
 const positions=new Map<string,Position3>(),chars=nodes.filter(n=>n.kind==='character'),prints=nodes.filter(n=>n.id!==anchor&&isSeal(n))
 if(nodes.some(n=>n.id===anchor))positions.set(anchor,{x:0,y:0,z:28})
 chars.forEach((n,i)=>{const a=-Math.PI/2+i*Math.PI*2/Math.max(chars.length,1);positions.set(n.id,{x:110*Math.cos(a),y:95*Math.sin(a),z:10+Math.sin(a*2)*18})})
 prints.forEach((n,i)=>{const a=-Math.PI/2+i*Math.PI*2/Math.max(prints.length,1);positions.set(n.id,{x:224*Math.cos(a),y:178*Math.sin(a),z:-20+Math.cos(a*2)*28})})
 for(const n of nodes)if(!positions.has(n.id))positions.set(n.id,{x:0,y:-220,z:0})
 return positions
}
export function characterFrequency(data:GraphData){
 const eligible=new Set(data.nodes.filter(n=>isSeal(n)&&n.matched!==false).map(n=>n.id))
 return data.nodes.filter(n=>n.kind==='character').map(node=>({node,count:new Set(data.edges.filter(e=>isAsserted(e)&&eligible.has(e.source)&&e.target===node.id&&e.predicate==='contains_character').map(e=>e.source)).size})).filter(r=>r.count).sort((a,b)=>b.count-a.count||a.node.label.localeCompare(b.node.label,'zh'))
}
export function sealDocuments(data:GraphData,id:string){const ids=new Set(data.edges.filter(e=>isAsserted(e)&&e.source===id).map(e=>e.document_id));const url=data.nodes.find(n=>n.id===id)?.attributes.url;return data.documents.filter(d=>ids.has(d.id)||d.url===url).sort((a,b)=>Number(b.url===url)-Number(a.url===url))}
export function comparedSeals(data:GraphData,a:string,b:string){
 const left=sealCharacters(data,a),right=sealCharacters(data,b),ids=new Set(right.map(r=>r.node.id))
 return {left,right,shared:left.filter(r=>ids.has(r.node.id)).map(r=>r.node),distinct:new Set([...left,...right].map(r=>r.node.id)).size}
}
