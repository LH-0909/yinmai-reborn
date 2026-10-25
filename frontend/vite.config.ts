import { defineConfig, normalizePath } from 'vite'
import vue from '@vitejs/plugin-vue'
import {existsSync,readFileSync,readdirSync,statSync,writeFileSync} from 'node:fs'
import {join} from 'node:path'
import {fileURLToPath} from 'node:url'
const portFile=new URL('../runtime/api-port.json',import.meta.url)
const apiPort=existsSync(portFile)?Number(JSON.parse(readFileSync(portFile,'utf8')).port):8000
if(!Number.isInteger(apiPort)||apiPort<1024||apiPort>65535)throw new Error('Invalid local API port; run scripts/dev.py start.')

// GitHub Pages serves this project from /<repo>/, but the UI hardcodes "/assets/…".
// Rewrite those absolute paths across the built files (JS/CSS/JSON) only.
function demoAssetBase(base:string){
 const walk=(dir:string,ext:RegExp)=>{
  for(const name of readdirSync(dir)){
   const full=join(dir,name)
   if(statSync(full).isDirectory()){walk(full,ext);continue}
   if(!ext.test(name))continue
   const text=readFileSync(full,'utf8')
   if(!text.includes('/assets/'))continue
   const marker='@@ASSET_BASE@@'
   const next=text.split(base+'assets/').join(marker).split('/assets/').join(base+'assets/').split(marker).join(base+'assets/')
   if(next!==text)writeFileSync(full,next)
  }
 }
 return {name:'demo-asset-base',closeBundle(){if(base!=='/')walk(fileURLToPath(new URL('./dist',import.meta.url)),/\.(js|css|json)$/)}}
}

export default defineConfig(({mode})=>{
 const demo=mode==='demo'
 const base=demo?'/yinmai-reborn/':'/'
 return {base,plugins:[vue(),...(demo?[demoAssetBase(base)]:[]),{name:'local-api-port',configureServer(server){const file=fileURLToPath(portFile);server.watcher.add(file);server.watcher.on('change',path=>{if(normalizePath(path)===normalizePath(file))void server.restart()})}}],server:{host:'127.0.0.1',port:5173,strictPort:true,allowedHosts:true,watch:{ignored:['**/.*.tmpdir/**','**/*.tmp']},proxy:{'/api':{target:'http://127.0.0.1:'+apiPort}}},build:{chunkSizeWarningLimit:900}}
})
