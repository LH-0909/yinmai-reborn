<script setup lang="ts">defineProps<{name:string;alt:string}>()</script>
<template><img class="im-art" :src="'/assets/museum/'+name+'.png'" :alt="alt" draggable="false"></template>
