<script setup lang="ts">
import {ref} from 'vue';import {IconArrowRight,IconCube,IconHandMove,IconBook,IconDeviceVisionPro,IconBroadcast,IconWorld} from '@tabler/icons-vue';import Rect from './Rect.vue';import Art from './Art.vue';import {show} from './state';import {current} from '../store'
const selected=ref(0)
const cards=[['AR体验','让古印活起来','experience-ar','通过AR技术，在现实空间中欣赏古印细节，360°互动探索。'],['数字展柜','珍品云端典藏','experience-cabinet','高清还原历代名印，支持多角度观赏与细节放大。'],['印章故事','一印一世界','experience-1','聆听印章背后的历史人物、文化典故与家国故事。'],['场景漫游','穿越时空的印迹','experience-2','沉浸式3D场景，漫游不同时期的印章文化场景。'],['语音讲解','AI伴您观展','experience-3','专业语音讲解，带您深入了解每一枚印章的来龙去脉。']]
function enter(i:number){selected.value=i;if(i===1)show('mesh','数字展柜 · 真实印面',{url:current.value?.artifacts.filter(a=>a.kind==='stl').at(-1)?.url});else if(i===2)show('stories','印章故事');else if(i===4)show('speech','语音讲解',{text:'印脉重生，以印为媒，连接传统与未来。当前展厅画面来自您提供的视觉参考。'});else show('experience',cards[i]![0],{index:i})}
</script>
<template>
<Rect :x="170" :y="0" :w="1502" :h="515" plain><Art name="experience-hero" alt="沉浸展厅，印脉重生数字博物馆视觉概念"/></Rect>
<Rect v-for="(c,i) in cards" :key="c[0]" :x="212+i*287" :y="515" :w="273" :h="288" :title="c[0]"><button class="im-experience-card" @click="enter(i)"><h2>{{c[0]}}</h2><h3>{{c[1]}}</h3><Art :name="c[2]!" :alt="c[0]+'场景参考'"/><p>{{c[3]}}</p><IconArrowRight class="im-tile-arrow" :size="27"/></button></Rect>
<Rect :x="406" :y="821" :w="268" :h="95" plain><div class="im-experience-features"><button v-for="(t,i) in ['沉浸体验','交互探索','文化传承']" @click="enter(i)"><component :is="[IconCube,IconHandMove,IconBook][i]" :size="28"/><b>{{t}}</b><small>{{['Immersive','Interactive','Heritage'][i]}}</small></button></div></Rect>
<Rect :x="781" :y="820" :w="292" :h="66" plain><button class="im-gold-button im-enter" @click="enter(selected)">立即进入 <IconArrowRight :size="23"/></button></Rect>
<Rect :x="1158" :y="821" :w="275" :h="95" plain><div class="im-experience-features"><button v-for="(t,i) in ['AR/VR','多感官体验','全球共享']" @click="show('experience',t,{index:i})"><component :is="[IconDeviceVisionPro,IconBroadcast,IconWorld][i]" :size="28"/><b>{{t}}</b><small>{{['Technology','Multi-sensory','Global'][i]}}</small></button></div></Rect>
</template>
