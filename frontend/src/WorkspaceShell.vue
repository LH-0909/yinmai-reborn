<script setup lang="ts">
import {computed,onMounted} from 'vue'
import {useRoute} from 'vue-router'
import {IconHome,IconArrowBigUp,IconCircle,IconSparkles,IconCube,IconBox,IconBooks,IconMessageChatbot,IconListDetails,IconX} from '@tabler/icons-vue'
import {seals,current,select,refresh,run,busy,message,error,health} from './store'
import Home from './pages/Home.vue'
import Upload from './pages/Upload.vue'
import Process from './pages/Process.vue'
import Reconstruct from './pages/Reconstruct.vue'
import Manufacture from './pages/Manufacture.vue'
import Knowledge from './pages/Knowledge.vue'
import Assistant from './pages/Assistant.vue'
import Projects from './pages/Projects.vue'
const route=useRoute()
const nav=[['首页','/workspace',IconHome],['印谱上传','/upload',IconArrowBigUp],['AI智能识别','/recognition',IconCircle],['AI修复','/restoration',IconSparkles],['三维重建','/reconstruction',IconCube],['实体制作','/manufacture',IconBox],['印谱知识库','/knowledge',IconBooks],['AI文化助手','/assistant',IconMessageChatbot],['项目管理','/projects',IconListDetails]] as const
const pages:Record<string,{title:string;subtitle:string}>={
 '/upload':{title:'印谱上传',subtitle:'将古籍中的平面印蜕，转化为可被识别与处理的高质量数字资料'},
 '/recognition':{title:'AI智能识别',subtitle:'印文提取与图像预处理 · AI识别结果保留人工校订'},
 '/restoration':{title:'AI古印智能修复',subtitle:'古印清污 · 残损修复 · 结构校订 · 印文保护'},
 '/reconstruction':{title:'三维重建与实体印面设计',subtitle:'从二维印文到可打印三维印面，支持实时旋转、参数化编辑及模型导出'},
 '/manufacture':{title:'实体印章制作与效果验证',subtitle:'将修复后的古印转化为可制造模型，完成实体盖印测试与实际效果记录'},
 '/knowledge':{title:'印谱知识库与历史文化检索',subtitle:'基于印文、形制、时代与文献索引的专题知识管理'},
 '/assistant':{title:'AI印文化与制印智能助手',subtitle:'用AI理解印章知识、篆刻工艺与数字制造流程'},
 '/projects':{title:'项目管理与数字资产中心',subtitle:'统一管理古印谱原稿、修复版本、三维模型与实体制作任务'}}
const page=computed(()=>pages[route.path]);onMounted(()=>refresh().catch(e=>error.value=e.message))
</script>
<template>
<aside class="sidebar"><RouterLink to="/" class="brand"><img src="/assets/brand.png" alt="印脉重生 文化·科技·智造"></RouterLink><nav aria-label="主要导航"><RouterLink v-for="[label,path,icon] in nav" :key="path" :to="path" :aria-label="label" :class="{active:route.path===path}"><component :is="icon" :size="23" :stroke-width="1.7"/><span>{{label}}</span></RouterLink></nav><footer><span>传承印文化</span><strong>科技续文脉</strong><p>AI ×</p><p>HARMONYOS</p></footer></aside>
<header class="topbar"><RouterLink to="/" class="top-title">印脉重生</RouterLink><span class="top-subtitle">古印谱数字复原与实体印章智能再造系统</span><div class="top-right"><span class="top-motto">千年印脉　·　数字新生</span><span :class="['pill',health?'green':'']">{{health?'数据库已连接':'连接检查中'}}</span><span class="avatar">印</span><select aria-label="当前印谱" :disabled="busy" :value="current?.id||'__reference__'" @change="select(($event.target as HTMLSelectElement).value)"><option value="__reference__">界面参考（不可处理）</option><option v-for="s in seals" :value="s.id" :key="s.id">{{s.title}}</option></select></div></header>
<main><div v-if="page" class="page-heading"><div><h1>{{page.title}}</h1><p>{{page.subtitle}}</p></div><div class="heading-tags"><span class="pill">古印数字化 · AI智能再造</span><span v-if="route.path==='/reconstruction'" class="pill green">Three.js · STL</span><RouterLink v-if="route.path==='/projects'" class="button primary small" to="/upload">+ 新建印谱项目</RouterLink></div></div>
<Home v-if="route.path==='/workspace'"/><Upload v-else-if="route.path==='/upload'"/><Process v-else-if="route.path==='/recognition'||route.path==='/restoration'" :key="route.path" :mode="route.path==='/restoration'?'restoration':'recognition'"/><Reconstruct v-else-if="route.path==='/reconstruction'"/><Manufacture v-else-if="route.path==='/manufacture'"/><Knowledge v-else-if="route.path==='/knowledge'"/><Assistant v-else-if="route.path==='/assistant'"/><Projects v-else-if="route.path==='/projects'"/>
</main><div v-if="message" class="toast" role="status">{{message}}<button aria-label="关闭提示" @click="message=''"><IconX :size="16"/></button></div><div v-if="error" class="toast error" role="alert">{{error}}<button aria-label="关闭错误" @click="error=''"><IconX :size="16"/></button></div><div v-if="busy" class="busy" role="status">正在处理，请稍候…</div>
</template>
