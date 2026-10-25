<script setup lang="ts">
import {ref,onMounted,onBeforeUnmount,watch,nextTick} from 'vue'
import cytoscape,{type Core} from 'cytoscape'
import type {GraphData} from './types'
const props=withDefaults(defineProps<{data:GraphData|null;selected?:string;path?:string[];compact?:boolean;layout?:'radial'|'hierarchy';center?:string;depth?:number}>(),{layout:'radial',depth:1})
const emit=defineEmits<{select:[id:string,type:'node'|'edge']}>()
const holder=ref<HTMLDivElement>(),visibleCount=ref(0),centerLabel=ref('');let cy:Core|undefined;let observer:ResizeObserver|undefined
const colors:Record<string,string>={seal_object:'#bfa377',seal_draft:'#b34231',character:'#c09550',script:'#987947',seal_type:'#6a80a2',collection:'#9a78aa',resource:'#847d5c',document:'#6b8e9a',person:'#c29a64',period:'#9c8b62',place:'#a7854e'}
function render(){
 if(!cy||!props.data)return
 const root=props.center&&props.data.nodes.some(n=>n.id===props.center)?props.center:props.data.nodes.find(n=>(n.kind==='seal_draft'||n.kind==='seal_object'))?.id||props.data.nodes[0]?.id
 centerLabel.value=props.data.nodes.find(n=>n.id===root)?.label||''
 const distances=new Map<string,number>();if(root)distances.set(root,0)
 const queue=root?[root]:[];for(let i=0;i<queue.length;i++){const id=queue[i];for(const edge of props.data.edges){const other=edge.source===id?edge.target:edge.target===id?edge.source:'';if(other&&!distances.has(other)){distances.set(other,distances.get(id)!+1);queue.push(other)}}}
 const visible=props.data.nodes.filter(n=>props.depth===0||distances.has(n.id)&&distances.get(n.id)!<=props.depth||props.path?.includes(n.id))
 const ids=new Set(visible.map(n=>n.id));visibleCount.value=visible.length
 const edges=props.data.edges.filter(e=>ids.has(e.source)&&ids.has(e.target))
 const elements=[...visible.map((n,i)=>({data:{id:n.id,label:n.label,color:colors[n.kind]||'#957347',size:n.id===root?78:(n.kind==='seal_draft'||n.kind==='seal_object')?59:n.kind==='character'?42:49,level:distances.get(n.id)??6},classes:(n.id===root?'root ':'')+(!n.matched?'context':''),position:{x:350+250*Math.cos(i*2*Math.PI/visible.length),y:230+190*Math.sin(i*2*Math.PI/visible.length)}})),...edges.map(e=>({data:{id:e.id,source:e.source,target:e.target,label:e.label,status:e.status},classes:e.status==='candidate'?'candidate':e.status==='rejected'?'rejected':''}))]
 cy.elements().remove();cy.add(elements)
 if(props.layout==='hierarchy')cy.layout({name:'breadthfirst',directed:false,roots:root?[root]:undefined,circle:false,grid:false,animate:false,fit:true,padding:30,spacingFactor:.78,avoidOverlap:true,nodeDimensionsIncludeLabels:true}).run()
 else cy.layout({name:'concentric',concentric:n=>10-Number(n.data('level')),levelWidth:()=>1,minNodeSpacing:20,padding:props.compact?20:35,avoidOverlap:true,nodeDimensionsIncludeLabels:true,animate:false,fit:true,startAngle:-Math.PI/2,clockwise:true,equidistant:false}).run()
 mark()
}
function mark(){if(!cy)return;cy.elements().removeClass('active trail');if(props.selected)cy.getElementById(props.selected).addClass('active');if(props.path?.length)cy.elements().filter(e=>props.path!.includes(e.id())).addClass('trail')}
onMounted(()=>{
 cy=cytoscape({container:holder.value,style:[
  {selector:'node',style:{'background-color':'data(color)',label:'data(label)',width:'data(size)',height:'data(size)','border-width':2,'border-color':'#c7a46a',color:'#f4e2b9','font-family':'MuseumSong, Noto Serif SC, serif','font-size':14,'text-valign':'bottom','text-margin-y':9,'text-outline-color':'#14110d','text-outline-width':2,'text-wrap':'wrap','text-max-width':'115px'}},
  {selector:'node.root',style:{'border-color':'#f9cb79','border-width':3,'font-size':17,'font-weight':'bold','overlay-color':'#b98035','overlay-opacity':.07,'overlay-padding':15}},
  {selector:'node.context',style:{'border-style':'dashed'}},
  {selector:'edge',style:{width:1.2,'line-color':'#967844','target-arrow-color':'#967844','target-arrow-shape':'triangle','curve-style':'bezier',label:props.compact?'':'data(label)',color:'#b4a07c','font-size':10,'text-rotation':'autorotate','text-background-color':'#100e0a','text-background-opacity':.9,'text-background-padding':'2px'}},
  {selector:'.candidate',style:{'line-style':'dashed','line-color':'#b88e4b'}},
  {selector:'.rejected',style:{'line-style':'dotted',opacity:.4}},
  {selector:'node.active',style:{'border-color':'#ffe3a0','border-width':4,'overlay-color':'#dca456','overlay-opacity':.16,'overlay-padding':9}},
  {selector:'edge.active',style:{'line-color':'#ffe3a0',width:3,'target-arrow-color':'#ffe3a0'}},
  {selector:'node.trail',style:{'border-color':'#ffb84d','border-width':4}},
  {selector:'edge.trail',style:{'line-color':'#ffb84d','target-arrow-color':'#ffb84d',width:4}}
 ],minZoom:.15,maxZoom:3,boxSelectionEnabled:false})
 cy.on('tap','node',e=>emit('select',e.target.id(),'node'));cy.on('tap','edge',e=>emit('select',e.target.id(),'edge'))
 observer=new ResizeObserver(()=>{cy?.resize();cy?.fit(undefined,props.compact?20:40)});observer.observe(holder.value!);render()
 document.fonts.ready.then(()=>{if(cy)render()})
})
watch(()=>props.data,async()=>{await nextTick();render()})
watch(()=>[props.layout,props.center,props.depth],render)
watch(()=>props.path,render,{deep:true})
watch(()=>[props.selected,props.path],mark,{deep:true})
onBeforeUnmount(()=>{observer?.disconnect();cy?.destroy();cy=undefined})
function fit(){cy?.fit(undefined,32)}
defineExpose({fit})
</script>
<template><div class="kg-canvas-wrap"><div ref="holder" class="kg-canvas" role="img" :aria-label="(layout==='radial'?'中心辐射':'分层结构')+'知识图谱，当前展开'+visibleCount+'个节点。可点击节点和关系；也可从节点目录选择。'"></div><div v-if="!compact&&data?.nodes.length" class="kg-canvas-caption"><b>{{layout==='radial'?'中心辐射':'分层结构'}} · {{centerLabel}}</b><span>展开 {{visibleCount}} / {{data?.nodes.length}} 个节点 · 虚线边框为检索上下文</span></div><div v-if="!compact" class="kg-canvas-tools"><button aria-label="放大图谱" @click="cy?.zoom(cy.zoom()*1.25)">＋</button><button aria-label="缩小图谱" @click="cy?.zoom(cy.zoom()/1.25)">−</button><button @click="fit">适合画布</button></div><div v-if="!data?.nodes.length" class="kg-empty">当前筛选没有节点</div></div></template>
<style scoped>
.kg-canvas-wrap{position:relative;width:100%;height:100%;min-height:230px;overflow:hidden;background:radial-gradient(ellipse at center,#26211555,transparent 65%),#0f0d0a}.kg-canvas{position:absolute;inset:0}.kg-canvas-tools{position:absolute;right:15px;bottom:15px;display:flex;gap:5px}.kg-canvas-tools button{color:#e5d1a4;background:#1a1610;border:1px solid #74613c;border-radius:4px;padding:6px 11px;cursor:pointer;font:inherit;font-size:12px}.kg-empty{position:absolute;top:48%;width:100%;text-align:center;color:#b8aa8d;pointer-events:none}.kg-canvas-caption{position:absolute;left:16px;top:12px;pointer-events:none;max-width:80%;font-size:11px;color:#cfb784}.kg-canvas-caption b{font-weight:500;display:block}.kg-canvas-caption span{font-size:10px;color:#92866d}
</style>
