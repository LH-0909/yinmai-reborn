<script setup lang="ts">
import {computed} from 'vue';import {useRoute} from 'vue-router';import frames from './frames.json'
const props=defineProps<{x:number;y:number;w:number;h:number;plain?:boolean;title?:string}>(),route=useRoute()
const frame=computed(()=>{const page=route.path==='/'?'home':route.path.startsWith('/catalog/')?'detail':route.path.slice(1);const name=(frames as Record<string,string>)[`${page}:${props.x}:${props.y}:${props.w}:${props.h}`];return name?`url('/assets/museum/${name}.png')`:undefined})
</script>
<template><section :class="['im-rect',plain?'im-plain':'im-panel']" :aria-label="title" :style="{left:x+'px',top:y+'px',width:w+'px',height:h+'px','--im-mobile-ratio':w+'/'+h,'--im-panel-frame':frame}"><slot/></section></template>
