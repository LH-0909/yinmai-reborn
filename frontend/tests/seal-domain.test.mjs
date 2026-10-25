import assert from 'node:assert/strict'
import test from 'node:test'
import {readFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import ts from 'typescript'
const source=await readFile(new URL('../src/graph/seal-domain.ts',import.meta.url),'utf8')
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText
const {previewFor,sealCharacters,relatedSeals,sealContext,sealOrbitPositions,characterFrequency,comparedSeals,sealDocuments,museumRecordFor,museumReadingData}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'))
const seed=JSON.parse(await readFile(new URL('../../data/knowledge-graph/verified-public-metadata.json',import.meta.url),'utf8'))
const data={...seed,nodes:seed.nodes.map(n=>({...n,matched:true})),edges:seed.edges.map(e=>({...e,source:e.subject,target:e.object}))}
const registry=JSON.parse(await readFile(new URL('../src/graph/seal-previews.json',import.meta.url),'utf8'))
const anchor=data.nodes.find(n=>n.label==='人生一梦'),dream=data.nodes.find(n=>n.label==='梦'),other=data.nodes.find(n=>n.label==='人生如梦')
const museumSeed=JSON.parse(await readFile(new URL('../../data/knowledge-graph/verified-museum-seals.json',import.meta.url),'utf8'))
const museums=JSON.parse(await readFile(new URL('../../data/heritage/core-museum-records.json',import.meta.url),'utf8'))
const museumData={...data,nodes:[...new Map([...data.nodes,...museumSeed.nodes.map(n=>({...n,matched:true}))].map(n=>[n.id,n])).values()],edges:[...data.edges,...museumSeed.edges.map(e=>({...e,source:e.subject,target:e.object}))],documents:[...data.documents,...museumSeed.documents]}

test('physical gallery requires exact official accession, page receipt and object identity',()=>{
 const objects=museumData.nodes.filter(n=>n.kind==='seal_object');assert.equal(objects.length,3)
 for(const n of objects){assert(museumRecordFor(n,museumData,museums));assert.equal(museumRecordFor({...n,attributes:{...n.attributes,accession_number:'故00000000'}},museumData,museums),undefined)}
 assert.equal(museumRecordFor(anchor,museumData,museums),undefined)
 assert.equal(museumRecordFor({...objects[0],id:anchor.id},museumData,museums),undefined)
 const row=museums[objects[0].id]
 const wrongImpression={...museums,[objects[0].id]:{...row,impression:{...row.impression,display_url:museums[objects[1].id].impression.display_url}}}
 assert.equal(museumRecordFor(objects[0],museumData,wrongImpression),undefined)
 const forged={...museumData,documents:museumData.documents.map(d=>d.id===row.document_id?{...d,sha256:'0'.repeat(64)}:d)}
 assert.equal(museumRecordFor(objects[0],forged,museums),undefined)
})

test('an official-looking URL or manual claim does not establish a physical collection object',()=>{
 const object=museumData.nodes.find(n=>n.kind==='seal_object'),row=museums[object.id]
 const pending={...museumData,edges:museumData.edges.map(e=>e.source===object.id?{...e,status:'candidate'}:e)}
 assert.equal(museumRecordFor(object,pending,museums),undefined)
 const manual={...museumData,documents:museumData.documents.map(d=>d.id===row.document_id?{...d,method:'manual_citation_not_fetched',fetched_at:null}:d)}
 assert.equal(museumRecordFor(object,manual,museums),undefined)
 assert.equal(museumRecordFor(object,{...museumData,documents:[]},museums),undefined)
})

test('physical gallery excludes all fourteen unproven draft objects from scope and frequency',()=>{
 assert.equal(museumReadingData(data,museums).nodes.length,0)
 const scope=museumReadingData(museumData,museums)
 assert.equal(scope.nodes.filter(n=>n.kind==='seal_object').length,3)
 assert(!scope.nodes.some(n=>n.kind==='seal_draft'))
 assert(scope.edges.every(e=>museums[e.source]&&e.document_id===museums[e.source].document_id))
 assert.equal(characterFrequency(scope).find(r=>r.node.label==='宝').count,3)
 const main=scope.nodes.find(n=>n.label==='皇帝尊亲之宝')
 assert.equal(relatedSeals(scope,main.id).length,2)
 assert.equal(sealContext(scope,main.id,'read','',museums).nodes.length,7)
})

test('three official photos and impressions preserve source captions, identities and file hashes',async()=>{
 assert.equal(Object.keys(museums).length,3)
 for(const [id,row] of Object.entries(museums)){
  const object=museumData.nodes.find(n=>n.id===id);assert(previewFor(object,museums))
  assert.equal(row.impression.caption,row.official_title+'钤本')
  for(const [variant,record] of [['photo',row],['impression',row.impression]]){
   const filename=id+(variant==='photo'?'':'-impression')+'.webp'
   assert.equal(record.display_url,'/assets/seal-previews/'+filename)
   assert.equal(new URL(record.image_url).hostname,'img.dpm.org.cn')
   const raw=await readFile(new URL('../public'+record.display_url,import.meta.url));assert.equal(createHash('sha256').update(raw).digest('hex'),record.preview_sha256)
   assert(record.width>0&&record.height>0)
  }
 }
})
test('a preview requires matching object ID, title, page URL and bounded local path',()=>{
 assert(previewFor(anchor,registry));assert.equal(previewFor({...anchor,label:'不同释文'},registry),undefined)
 assert.equal(previewFor({...anchor,attributes:{url:'https://other.example/1'}},registry),undefined)
 assert.equal(previewFor(anchor,{[anchor.id]:{...registry[anchor.id],display_url:'https://external.example/image.png'}}),undefined)
 assert.equal(previewFor(dream,registry),undefined)
})
test('reading order comes from recorded positions and excludes unrelated node labels',()=>{
 assert.equal(sealCharacters(data,anchor.id).map(r=>r.node.label).join(''),'人生一梦')
 const irrelevant={...data,nodes:[...data.nodes,{id:'unused',label:'假',kind:'character'}]}
 assert(!sealCharacters(irrelevant,anchor.id).some(r=>r.node.id==='unused'))
})
test('related prints and comparison use shared transcriptions, never fabricated inter-seal claims',()=>{
 const related=relatedSeals(data,anchor.id,dream.id);assert.equal(related.length,3)
 assert(related.every(r=>r.shared.every(c=>c.node.id===dream.id)))
 const comparison=comparedSeals(data,anchor.id,other.id)
 assert.deepEqual(new Set(comparison.shared.map(n=>n.label)),new Set(['人','生','梦']))
 assert(!related.some(r=>r.node.id===anchor.id))
})
test('reading and association scopes preserve actual evidence IDs and original data',()=>{
 const original=JSON.stringify(data),read=sealContext(data,anchor.id,'read','',registry)
 assert.equal(read.nodes.length,5);assert.equal(read.edges.length,4)
 const context=sealContext(data,anchor.id,'related',dream.id,registry),ids=new Set(context.nodes.map(n=>n.id))
 assert.equal(context.nodes.length,5);assert.equal(context.edges.length,4)
 assert(context.edges.every(e=>data.edges.some(x=>x.id===e.id)&&ids.has(e.source)&&ids.has(e.target)&&e.predicate==='contains_character'))
 assert(!context.nodes.some(n=>n.kind==='person'||n.kind==='period'||n.kind==='resource'))
 assert.equal(JSON.stringify(data),original);assert.equal(sealContext(data,'missing','related').nodes.length,0)
})
test('spatial reading layout has only visible IDs, a real anchor and finite deterministic positions',()=>{
 const context=sealContext(data,anchor.id,'related','',registry),a=sealOrbitPositions(context.nodes,anchor.id),b=sealOrbitPositions(context.nodes,anchor.id)
 assert.deepEqual(a,b);assert.equal(a.size,context.nodes.length);assert.deepEqual(a.get(anchor.id),{x:0,y:0,z:28})
 assert([...a.values()].every(p=>Object.values(p).every(Number.isFinite)))
 assert.equal(sealOrbitPositions([],'missing').size,0)
})
test('character counts measure distinct actual seal records even if an edge is duplicated',()=>{
 const first=characterFrequency(data),duplicated={...data,edges:[...data.edges,...data.edges]}
 assert.deepEqual(characterFrequency(duplicated).map(r=>[r.node.id,r.count]),first.map(r=>[r.node.id,r.count]))
 assert.equal(first.find(r=>r.node.id===dream.id).count,4)
})
test('all fourteen packaged previews match original record identity and verified file hashes',async()=>{
 assert.equal(Object.keys(registry).length,14)
 for(const row of Object.values(registry)){
  assert(previewFor(data.nodes.find(n=>n.id===row.node_id),registry))
  const file=await readFile(new URL('../public'+row.display_url,import.meta.url))
  assert.equal(createHash('sha256').update(file).digest('hex'),row.preview_sha256)
  assert(row.width>0&&row.height>0&&row.width<=960&&row.height<=960)
 }
})
test('candidate/rejected claims cannot become reading text, related prints or statistics',()=>{
 for(const status of ['candidate','rejected']){
  const pending={...data,edges:data.edges.map(e=>({...e,status}))}
  assert.equal(sealCharacters(pending,anchor.id).length,0);assert.equal(relatedSeals(pending,anchor.id).length,0)
  assert.equal(characterFrequency(pending).length,0);assert.equal(sealContext(pending,anchor.id,'related').edges.length,0)
 }
 const scoped={...data,nodes:data.nodes.map(n=>n.id===other.id?{...n,matched:false}:n)}
 assert(!relatedSeals(scoped,anchor.id).some(r=>r.node.id===other.id))
 // A context character is still valid reading evidence; matched is a search
 // dimension, independent of trust, and must not erase an asserted transcript.
 const charsAsContext={...data,nodes:data.nodes.map(n=>n.kind==='character'?{...n,matched:false}:n)}
 assert.equal(sealCharacters(charsAsContext,anchor.id).length,4)
})
test('parallel documentary evidence stays available without double-counting letters or claims',()=>{
 const edge=data.edges.find(e=>e.source===anchor.id&&e.target===dream.id)
 const parallel={...data,edges:[...data.edges,{...edge,id:'parallel-evidence',document_id:'another-document'}]}
 assert.equal(sealCharacters(parallel,anchor.id).length,4)
 assert.equal(sealCharacters(parallel,anchor.id).find(r=>r.node.id===dream.id).evidenceEdges.length,2)
 const context=sealContext(parallel,anchor.id,'read')
 assert.equal(context.edges.length,4)
 const merged=context.edges.find(e=>e.target===dream.id)
 assert.deepEqual(new Set(merged.attributes.evidence_edge_ids),new Set([edge.id,'parallel-evidence']))
 assert.deepEqual(new Set(merged.attributes.evidence_document_ids),new Set([edge.document_id,'another-document']))
})
test('registry cross-object IDs, cross-object filenames and invalid dimensions are rejected',()=>{
 const row=registry[anchor.id]
 for(const bad of [{...row,node_id:other.id},{...row,display_url:registry[other.id].display_url},{...row,width:0},{...row,height:Infinity}])assert.equal(previewFor(anchor,{[anchor.id]:bad}),undefined)
 const nonsquare={...row,width:120,height:240},context=sealContext(data,anchor.id,'read','',{[anchor.id]:nonsquare})
 assert.equal(context.nodes.find(n=>n.id===anchor.id).attributes.preview_width,120)
 assert.equal(context.nodes.find(n=>n.id===anchor.id).attributes.preview_height,240)
})
test('image source document wins over first-edge order and candidate documents',()=>{
 const original=data.documents.find(d=>d.url===anchor.attributes.url),edge=data.edges.find(e=>e.source===anchor.id)
 const extended={...data,documents:[{...original,id:'unrelated-doc',url:'https://yingaoku.cn/seal/999'},...data.documents],edges:[{...edge,id:'candidate-first',status:'candidate',document_id:'unrelated-doc'},...data.edges]}
 assert.equal(sealDocuments(extended,anchor.id)[0].id,original.id)
 assert(!sealDocuments(extended,anchor.id).some(d=>d.id==='unrelated-doc'))
})
