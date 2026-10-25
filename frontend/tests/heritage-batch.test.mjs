import assert from 'node:assert/strict'
import test from 'node:test'
import {readFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import ts from 'typescript'
const json=async path=>JSON.parse(await readFile(new URL(path,import.meta.url),'utf8'))
const seeds=await Promise.all(['verified-public-metadata','verified-museum-seals','verified-museum-expansion'].map(x=>json('../../data/knowledge-graph/'+x+'.json')))
const data=Object.fromEntries(['nodes','edges','documents','sources'].map(k=>[k,[...new Map(seeds.flatMap(s=>s[k]).map(r=>[r.id,r])).values()]]))
data.nodes=data.nodes.map(n=>({...n,matched:true}));data.edges=data.edges.map(e=>({...e,source:e.subject,target:e.object}))
const registry=await json('../src/graph/museum-seals.json'),canonical=await json('../../data/heritage/records.json'),books=await json('../../data/heritage/bibliography.json')
const js=ts.transpileModule(await readFile(new URL('../src/graph/seal-domain.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText
const {museumRecordFor,museumReadingData,relatedSeals,sealContext,previewFor}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'))

test('all 125 published records pass official object/document identity checks across three institutions',()=>{
 assert.deepEqual(registry,canonical);assert.equal(Object.keys(registry).length,125)
 assert.equal(data.nodes.length,555);assert.equal(data.edges.length,1013);assert.equal(data.documents.length,170)
 const objects=data.nodes.filter(n=>n.kind==='seal_object');assert.equal(objects.length,125)
 assert.deepEqual(objects.filter(n=>!museumRecordFor(n,data,registry)).map(n=>n.label),[])
 const scope=museumReadingData(data,registry)
 assert.equal(scope.nodes.filter(n=>n.kind==='seal_object').length,125)
 assert(!scope.nodes.some(n=>n.kind==='seal_draft'))
 assert.deepEqual(new Set(Object.values(registry).map(r=>r.source_id)),new Set(['dpm','nmc','nyw']))
})
test('every photo and each of the 106 actual impressions retains a matching local SHA256',async()=>{
 let impressions=0
 for(const [id,r] of Object.entries(registry))for(const [suffix,img] of [['',r],['-impression',r.impression]]){
  if(!img)continue;if(suffix)impressions++
  assert.equal(img.display_url,'/assets/seal-previews/'+id+suffix+'.webp')
  assert.equal(createHash('sha256').update(await readFile(new URL('../public'+img.display_url,import.meta.url))).digest('hex'),img.preview_sha256)
  assert(img.width>0&&img.height>0)
 }
 assert.equal(impressions,106)
})
test('source-native characters and missing accessions are preserved without inferred identifiers',()=>{
 const cross=Object.values(registry).filter(r=>r.source_id!=='dpm');assert.equal(cross.length,5)
 for(const r of cross){assert.equal(r.accession_number,'');assert(r.catalogue_record_id);assert.equal(r.identifier_label,'官方条目号（非文物号）')}
 const seal=cross.find(r=>r.official_title.includes('君之信'));assert.equal(seal.transcription,'君之信鉩')
 const n=data.nodes.find(n=>n.id===seal.node_id)
 assert.equal(museumRecordFor({...n,attributes:{...n.attributes,catalogue_record_id:'000'}},data,registry),undefined)
})
test('gallery caption aliases require documented exact complete inscription; missing impressions remain honest',()=>{
 const alias=Object.values(registry).find(r=>r.caption!==r.official_title);assert(alias)
 const n=data.nodes.find(n=>n.id===alias.node_id)
 assert.equal(museumRecordFor(n,data,{...registry,[n.id]:{...alias,image_match_basis:''}}),undefined)
 const other=Object.values(registry).find(r=>r.source_id!==alias.source_id)
 assert.equal(museumRecordFor(n,data,{...registry,[n.id]:{...alias,image_url:other.image_url}}),undefined)
 const missing=Object.values(registry).find(r=>!r.impression);assert(missing)
 assert(museumRecordFor(data.nodes.find(n=>n.id===missing.node_id),data,registry))
 const unavailable={...missing,status:'unavailable',display_url:'',width:0,height:0}
 assert(museumRecordFor(data.nodes.find(n=>n.id===missing.node_id),data,{...registry,[missing.node_id]:unavailable}))
 assert.equal(previewFor(data.nodes.find(n=>n.id===missing.node_id),{[missing.node_id]:unavailable}),undefined)
})
test('five differing period classifications have both source values and no asserted dating edge',()=>{
 const rows=Object.values(registry).filter(r=>r.period_conflict);assert.equal(rows.length,5)
 for(const r of rows){assert(r.period_index&&r.period_body&&r.period_index!==r.period_body);assert(r.period.includes('待核对'));assert(!data.edges.some(e=>e.source===r.node_id&&e.predicate==='dated_to'))}
})
test('association is capped at eight displayed objects while retaining all shared-character search results',()=>{
 const scope=museumReadingData(data,registry),anchor=scope.nodes.filter(n=>n.kind==='seal_object').sort((a,b)=>relatedSeals(scope,b.id).length-relatedSeals(scope,a.id).length)[0]
 assert(relatedSeals(scope,anchor.id).length>8)
 const display=sealContext(scope,anchor.id,'related','',registry,8)
 assert.equal(display.nodes.filter(n=>n.kind==='seal_object').length,9)
 assert(display.edges.every(e=>e.predicate==='contains_character'))
})
test('20 official bibliographic citations are never presented as texts already read',()=>{
 assert.equal(books.length,20);assert.equal(books.filter(b=>b.kind==='paper').length,10)
 for(const b of books){assert.equal(b.full_text_read,false);assert.equal(b.access_state,'catalogue_citation_only');assert(data.documents.some(d=>d.id===b.receipt_document_id&&d.sha256))}
 assert(books.some(b=>b.publication_as_listed==='16册'))
})
