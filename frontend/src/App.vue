<script setup lang="ts">
import {computed,defineAsyncComponent} from 'vue';import {useRoute} from 'vue-router';import MuseumShell from './museum/MuseumShell.vue';import WorkspaceShell from './WorkspaceShell.vue'
const GraphPage=defineAsyncComponent(()=>import('./graph/GraphPage.vue'))
const route=useRoute(),museum=computed(()=>['/','/customize','/catalog','/culture','/experience','/account'].includes(route.path)||route.path.startsWith('/catalog/'))
</script>
<template><GraphPage v-if="route.path==='/graph'"/><MuseumShell v-else-if="museum"/><WorkspaceShell v-else/></template>
