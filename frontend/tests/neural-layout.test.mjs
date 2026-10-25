import assert from 'node:assert/strict'
import test from 'node:test'
import {readFile} from 'node:fs/promises'
import ts from 'typescript'
import * as THREE from 'three'
const file=new URL('../src/graph/neural-layout.ts',import.meta.url)
const js=ts.transpileModule(await readFile(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText
const {graphScope,neuralPositions,flowAssignments,nearestGraphHit}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'))
const seed=JSON.parse(await readFile(new URL('../../data/knowledge-graph/verified-public-metadata.json',import.meta.url),'utf8'))
const data={...seed,nodes:seed.nodes.map(n=>({...n,matched:true})),edges:seed.edges.map(e=>({...e,source:e.subject,target:e.object}))}

test('all actual claims retain their real endpoints in the 3D scope',()=>{
 const scope=graphScope(data,'',0);assert.equal(scope.nodes.length,61);assert.equal(scope.edges.length,126)
 const ids=new Set(scope.nodes.map(n=>n.id));assert(scope.edges.every(e=>ids.has(e.source)&&ids.has(e.target)))
 const original=new Set(data.edges.map(e=>e.id));assert(scope.edges.every(e=>original.has(e.id)))
})
test('one-hop scope excludes unrelated records and includes explicit path context',()=>{
 const seal=data.nodes.find(n=>n.label==='人生一梦'),other=data.nodes.find(n=>n.label==='浮生记趣')
 const scope=graphScope(data,seal.id,1);assert.equal(scope.nodes.length,9);assert(!scope.nodes.some(n=>n.id===other.id))
 const path=graphScope(data,seal.id,1,[other.id]);assert(path.nodes.some(n=>n.id===other.id));assert(path.edges.every(e=>data.edges.some(d=>d.id===e.id)))
})
test('spatial layout is finite, deterministic and preserves source data',()=>{
 const original=JSON.stringify(data),first=neuralPositions(data.nodes,data.edges),second=neuralPositions(data.nodes,data.edges)
 assert.deepEqual(first,second);assert.equal(JSON.stringify(data),original)
 assert.equal(first.size,data.nodes.length);assert([...first.values()].every(p=>Object.values(p).every(Number.isFinite)))
 assert(new Set([...first.values()].map(p=>JSON.stringify(p))).size===data.nodes.length)
 assert(neuralPositions([],[]).size===0)
})
test('every moving particle belongs to an existing relation and budget is bounded',()=>{
 const flow=flowAssignments(data.edges,900),ids=new Set(data.edges.map(e=>e.id));assert.equal(flow.length,756)
 assert(flow.every(p=>ids.has(p.edgeId)&&p.phase>=0&&p.phase<1&&p.speed>0));assert.deepEqual(flowAssignments([],900),[])
 assert.equal(flowAssignments(data.edges,25).length,25)
 assert.equal(flowAssignments(data.edges.map(e=>({...e,status:'candidate'})),900).length,0)
 assert.equal(flowAssignments(data.edges.map(e=>({...e,status:'rejected'})),900).length,0)
 const filtered=data.edges.slice(0,2);assert(flowAssignments(filtered).every(p=>filtered.some(e=>e.id===p.edgeId)))
})

test('real Three.js ray intersections respect depth for an overlapping line and node',()=>{
 const node=new THREE.Mesh(new THREE.SphereGeometry(1,12,8),new THREE.MeshBasicMaterial());node.position.z=-4;node.userData.type='node'
 const geometry=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-2,0,4),new THREE.Vector3(2,0,4)])
 const edge=new THREE.Line(geometry,new THREE.LineBasicMaterial());edge.userData.type='edge'
 node.updateMatrixWorld();edge.updateMatrixWorld();const ray=new THREE.Raycaster(new THREE.Vector3(0,0,10),new THREE.Vector3(0,0,-1));ray.params.Line.threshold=.25
 assert.equal(nearestGraphHit(ray.intersectObjects([node,edge],false)).object,edge)
 node.position.z=6;node.updateMatrixWorld();assert.equal(nearestGraphHit(ray.intersectObjects([node,edge],false)).object,node)
 assert.equal(nearestGraphHit([]),null)
 node.geometry.dispose();node.material.dispose();edge.geometry.dispose();edge.material.dispose()
})
