<script setup lang="ts">
import {computed} from 'vue'
import {IconSparkles,IconCube,IconGridDots,IconLayersIntersect} from '@tabler/icons-vue'
import Panel from '../components/Panel.vue'
import {seals,health,current} from '../store'
const artifacts=computed(()=>seals.value.flatMap(s=>s.artifacts));const models=computed(()=>artifacts.value.filter(a=>a.kind==='stl').length)
</script>
<template>
<section class="hero"><img class="hero-art" src="/assets/hero.png" alt="参考设计中的红石狮钮印章概念图"><div class="hero-copy"><p class="eyebrow">千年印脉 · 数字重生 · 文化智造</p><h1>印脉重生</h1><p class="hero-subtitle">古印谱数字复原与实体印章智能再造系统</p><div class="actions"><RouterLink to="/upload" class="button primary"><IconSparkles :size="17"/>开启古印复原</RouterLink><RouterLink to="/reconstruction" class="button"><IconCube :size="17"/>查看三维工作台</RouterLink></div></div></section>
<div class="metrics"><article><span>已归档印谱<IconGridDots/></span><strong>{{health?.counts.seals??'—'}}</strong></article><article><span>真实处理产物<IconSparkles/></span><strong>{{health?.counts.artifacts??'—'}}</strong></article><article><span>已生成印面模型<IconCube/></span><strong>{{models}}</strong></article><article><span>技术融合架构<IconLayersIntersect/></span><strong class="serif">端·云·智</strong></article></div>
<div class="home-grid"><Panel title="古印复原示范" note="原始印蜕 · 人工校订"><div class="home-compare"><div><span class="image-tag">{{current?'当前原图':'原始印蜕 · 参考素材'}}</span><img :src="current?.original_url||'/assets/home-original.png'" alt="原始古印图像"></div><b>➜</b><div><span class="image-tag">参考修复效果</span><img src="/assets/home-restored.png" alt="参考设计中的修复示意，非AI计算结果"></div></div></Panel><Panel title="三维实体预览" note="印面生成 · STL导出"><RouterLink to="/reconstruction" class="home-model"><span class="image-tag">狮钮印章 · 视觉概念参考</span><img src="/assets/home-model.png" alt="狮钮印章视觉概念示意"></RouterLink></Panel><Panel title="核心能力" note="从古籍到可盖印的实物"><div class="capabilities"><RouterLink to="/recognition"><b>AI智能识别</b><small>印文提取可用 · 篆字模型待接入</small></RouterLink><RouterLink to="/restoration"><b>古印缺损修复</b><small>OpenCV形态学处理 · 人工复核</small></RouterLink><RouterLink to="/reconstruction"><b>数字化实体智造</b><small>真实STL生成 · 朱白文与镜像</small></RouterLink></div></Panel></div>
<p class="home-footnote">原图中的统计数已替换为数据库实值。狮钮与复原图为提供的视觉参考素材，真实生成对象为印面浮雕。</p>
</template>
