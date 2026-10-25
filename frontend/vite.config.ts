import { defineConfig, normalizePath } from 'vite'
import vue from '@vitejs/plugin-vue'
import {existsSync,readFileSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
const portFile=new URL('../runtime/api-port.json',import.meta.url)
const apiPort=existsSync(portFile)?Number(JSON.parse(readFileSync(portFile,'utf8')).port):8000
if(!Number.isInteger(apiPort)||apiPort<1024||apiPort>65535)throw new Error('Invalid local API port; run scripts/dev.py start.')
export default defineConfig({plugins:[vue(),{name:'local-api-port',configureServer(server){const file=fileURLToPath(portFile);server.watcher.add(file);server.watcher.on('change',path=>{if(normalizePath(path)===normalizePath(file))void server.restart()})}}],server:{host:'127.0.0.1',port:5173,strictPort:true,proxy:{'/api':{target:'http://127.0.0.1:'+apiPort}}},build:{chunkSizeWarningLimit:900}})
