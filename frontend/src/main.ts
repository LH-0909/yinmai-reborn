import {createApp} from 'vue'
import {createRouter,createWebHistory} from 'vue-router'
import App from './App.vue'
import './style.css'
import './reading-theme.css'
const router=createRouter({history:createWebHistory(),scrollBehavior:(_to,_from,saved)=>saved||{top:0},routes:[{path:'/generate',redirect:'/'},...['/','/workspace','/graph','/customize','/catalog','/catalog/:slug','/culture','/experience','/account','/upload','/recognition','/restoration','/reconstruction','/manufacture','/knowledge','/assistant','/projects','/lab','/font'].map(path=>({path,component:{template:'<span></span>'}}))]})
createApp(App).use(router).mount('#app')
