<script setup lang="ts">defineProps<{active:number}>();const stages=[['上传印谱','/upload'],['AI识别','/recognition'],['智能修复','/restoration'],['三维重建','/reconstruction'],['实体制作','/manufacture']]</script>
<template><div class="workflow"><RouterLink v-for="(s,i) in stages" :key="s[1]" :to="s[1]" :class="{active:i===active}"><b>{{i+1}}</b>{{s[0]}}<span>→</span></RouterLink></div></template>
