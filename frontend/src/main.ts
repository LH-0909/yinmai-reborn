import {createApp} from 'vue'
import {createRouter,createWebHistory,createWebHashHistory} from 'vue-router'
import App from './App.vue'
import './style.css'
import './reading-theme.css'
import {isDemo} from './demo/demo'
import {installStaticApi} from './demo/static-backend'
if(isDemo)installStaticApi()
const WORKSPACE=['/workspace','/upload','/recognition','/restoration','/reconstruction','/manufacture','/knowledge','/assistant','/projects']
const router=createRouter({history:isDemo?createWebHashHistory():createWebHistory(),scrollBehavior:(_to,_from,saved)=>saved||{top:0},routes:[{path:'/generate',redirect:'/'},{path:'/lab',redirect:'/workspace'},{path:'/font',redirect:'/workspace'},...['/','/workspace','/graph','/customize','/catalog','/catalog/:slug','/culture','/experience','/account','/upload','/recognition','/restoration','/reconstruction','/manufacture','/knowledge','/assistant','/projects'].map(path=>({path,component:{template:'<span></span>'}}))]})
if(isDemo)router.beforeEach(to=>WORKSPACE.includes(to.path)?'/':true)
createApp(App).use(router).mount('#app')
