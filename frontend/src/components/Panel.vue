<script setup lang="ts">defineProps<{title:string;note?:string}>()</script>
<template><section class="panel"><header class="panel-title"><h2>{{title}}</h2><small>{{note}}</small></header><div class="panel-body"><slot/></div></section></template>
