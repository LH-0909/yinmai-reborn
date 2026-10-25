<script setup lang="ts">
// Interaction reference: Gezelli-z/moshi (MIT), graphConfig.js and KnowledgeGraph.jsx.
// This app uses actual IDs, actual evidence and an optional static reading layout.
import {ref,onMounted,onBeforeUnmount,watch,nextTick} from 'vue'
import * as echarts from 'echarts/core'
import {GraphChart,BarChart} from 'echarts/charts'
import {TooltipComponent,GridComponent} from 'echarts/components'
import {SVGRenderer} from 'echarts/renderers'
import type {GraphData} from './types'
import {sealOrbitPositions,characterFrequency} from './seal-domain'
echarts.use([GraphChart,BarChart,TooltipComponent,GridComponent,SVGRenderer])
const props=defineProps<{data:GraphData;anchor?:string;selected?:string;frequency?:boolean}>()
const emit=defineEmits<{select:[id:string,type:'node'|'edge']}>()
const holder=ref<HTMLDivElement>(),ready=ref(false);let chart:echarts.ECharts|undefined,observer:ResizeObserver|undefined
function draw(){
 if(!chart)return
 if(props.frequency){
  const rows=characterFrequency(props.data).slice(0,6).reverse()
  chart.setOption({animation:false,grid:{left:22,right:25,top:5,bottom:10},tooltip:{renderMode:'richText',formatter:(p:any)=>`${p.name} · ${p.value} 条印稿`},xAxis:{type:'value',show:false,minInterval:1},yAxis:{type:'category',triggerEvent:true,data:rows.map(r=>r.node.label),axisLine:{show:false},axisTick:{show:false},axisLabel:{color:'#c7b58e',fontSize:12}},series:[{type:'bar',data:rows.map(r=>({value:r.count,id:r.node.id,itemStyle:{color:r.node.id===props.selected?'#ca805f':'#9c7d48'}})),barWidth:8,label:{show:true,position:'right',color:'#c7b58e',fontSize:10},itemStyle:{borderRadius:2}}]},true)
 }else{
  const ps=sealOrbitPositions(props.data.nodes,props.anchor||'')
  chart.setOption({animation:false,tooltip:{renderMode:'richText',formatter:(p:any)=>p.dataType==='edge'?`${p.data.sourceLabel} → ${p.data.targetLabel}\n${p.data.value}`:`${p.name}\n${p.data.kindLabel}`},series:[{type:'graph',layout:'none',roam:true,draggable:true,scaleLimit:{min:.4,max:4},data:props.data.nodes.map(n=>({id:n.id,name:n.label,x:ps.get(n.id)?.x,y:ps.get(n.id)?.y,kindLabel:n.kind_label,symbol:n.attributes.display_preview?'image://'+n.attributes.display_preview:n.kind==='character'?'circle':'roundRect',symbolSize:n.attributes.display_preview?[(n.id===props.anchor?100:47)*Math.min(1,Number(n.attributes.preview_width)/Number(n.attributes.preview_height)||1),(n.id===props.anchor?100:47)*Math.min(1,Number(n.attributes.preview_height)/Number(n.attributes.preview_width)||1)]:24,symbolKeepAspect:true,itemStyle:{color:'#705532',borderColor:n.id===props.selected?'#d58b65':'#a88a55',borderWidth:1},label:{show:true,position:n.kind==='character'?'inside':'bottom',fontFamily:'serif',fontSize:n.kind==='character'?14:11,color:'#ead9b5',distance:8}})),links:props.data.edges.map(e=>({id:e.id,source:e.source,target:e.target,value:e.label,sourceLabel:props.data.nodes.find(n=>n.id===e.source)?.label,targetLabel:props.data.nodes.find(n=>n.id===e.target)?.label,lineStyle:{color:e.id===props.selected?'#cd8c65':'#a88a55',opacity:.55,width:1,curveness:.08}})),emphasis:{focus:'adjacency',lineStyle:{width:2,opacity:1}},edgeSymbol:['none','arrow'],edgeSymbolSize:[0,5]}]},true)
 }
}
onMounted(()=>{chart=echarts.init(holder.value!,undefined,{renderer:'svg'});chart.on('click',(p:any)=>{if(props.frequency){const id=p.componentType==='yAxis'?characterFrequency(props.data).find(r=>r.node.label===p.value)?.node.id:p.data?.id;if(id)emit('select',id,'node')}else if(p.data?.id)emit('select',p.data.id,p.dataType==='edge'?'edge':'node')});observer=new ResizeObserver(()=>chart?.resize());observer.observe(holder.value!);draw();ready.value=true})
watch(()=>[props.data,props.anchor,props.selected],async()=>{await nextTick();draw()})
onBeforeUnmount(()=>{observer?.disconnect();chart?.dispose();chart=undefined})
</script>
<template><div ref="holder" :class="frequency?'seal-frequency-chart':'seal-study-chart'" role="img" :aria-label="frequency?'当前资料汉字关联印稿数量，可点击图表汉字':`平面研读图谱，${data.nodes.length}个节点、${data.edges.length}条有据关系，可拖动、缩放和点击查看`" :data-chart-ready="ready" :data-chart-nodes="frequency?undefined:data.nodes.length" :data-chart-edges="frequency?undefined:data.edges.length"></div></template>
<style scoped>.seal-study-chart{width:100%;height:100%;min-height:430px}.seal-frequency-chart{width:100%;height:145px}</style>
