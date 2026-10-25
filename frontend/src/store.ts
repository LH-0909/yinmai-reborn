import {ref,computed} from 'vue'
export interface Artifact { id:string;kind:string;url:string;metadata:Record<string,any>;created_at:string }
export interface Seal { id:string;title:string;filename:string;source_kind:string;sha256:string;original_url:string;created_at:string;artifacts:Artifact[] }
export const seals=ref<Seal[]>([])
export const selectedId=ref(localStorage.getItem('yinmai-selected')||'')
export const current=computed(()=>seals.value.find(s=>s.id===selectedId.value))
export const health=ref<any>(null)
export const events=ref<any[]>([])
export const busy=ref(false)
export const message=ref('')
export const error=ref('')
let msgTimer:ReturnType<typeof setTimeout>
export function notify(text:string){message.value=text; clearTimeout(msgTimer);msgTimer=setTimeout(()=>message.value='',6000)}
export async function api<T=any>(path:string,options:RequestInit={}):Promise<T>{
 const res=await fetch('/api'+path,{...options,headers:options.body instanceof FormData?options.headers:{'Content-Type':'application/json',...options.headers}})
 if(!res.ok){let text='服务请求失败';try{const data=await res.json();text=typeof data.detail==='string'?data.detail:JSON.stringify(data.detail)}catch{}throw new Error(text)}
 return res.json()
}
export async function refresh(){[seals.value,health.value,events.value]=await Promise.all([api('/seals'),api('/health'),api('/events')]); if(!current.value && selectedId.value!=='__reference__' && seals.value.length)select(seals.value[0].id)}
export function select(id:string){selectedId.value=id;localStorage.setItem('yinmai-selected',id)}
export async function run(job:()=>Promise<void>){if(busy.value)return;busy.value=true;error.value='';try{await job()}catch(e){error.value=e instanceof Error?e.message:'操作失败'}finally{busy.value=false}}
export function date(value:string){return new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false})}
export function isProcessImage(a:Artifact){return ['original','extract','clean','repair','restoration','enhancement'].includes(a.kind)}
export const kindName:Record<string,string>={original:'原始扫描',extract:'印文提取',clean:'去噪版本',repair:'OpenCV修复',restoration:'AI修复',recognition:'AI识别',stl:'STL模型',enhancement:'实验去噪',annotation:'人工标注草稿',annotation_mask:'手绘掩膜'}
