import {ref} from 'vue'
import {api,notify,error,refresh,select,current} from '../store'
import {catalogSeed,type CatalogItem} from './data'
if(localStorage.getItem('yinmai-provenance-version')!=='20261023'){localStorage.setItem('yinmai-reference-mode','false');localStorage.setItem('yinmai-provenance-version','20261023')}
export const referenceMode=ref(localStorage.getItem('yinmai-reference-mode')==='true')
export const studio=ref<any>({favorites:[],designs:[],profile:{name:'山河未阑',bio:'以印为媒，连接传统与未来。'},counts:{designs:0,favorites:0,seals:0,ai_outputs:0}})
export const catalog=ref<CatalogItem[]>(catalogSeed)
export const modal=ref<{kind:string;title:string;data?:any}|null>(null)
export const globalSearch=ref(''),making=ref(false),latestComposition=ref<any>(null)
export const draft=ref({text:'',style:'秦篆',shape:'方章',material:'玉石',knob:'蟠龙',era:'汉代',polarity:'zhu',layout:'square',ink:'#b82e25',border:true,stroke_px:0})
export function show(kind:string,title:string,data?:any){modal.value={kind,title,data}}
export function restoreComposition(){if(referenceMode.value)return;const seal=current.value;if(seal?.source_kind==='native_typeset'&&!latestComposition.value){latestComposition.value={seal,preview_url:seal.artifacts.filter(a=>a.kind==='ink_preview').at(-1)?.url||seal.original_url};if(!draft.value.text)draft.value.text=seal.title}}
export function setReferenceMode(){referenceMode.value=!referenceMode.value;localStorage.setItem('yinmai-reference-mode',String(referenceMode.value));if(!referenceMode.value)restoreComposition()}
export async function loadStudio(){const [s,c]=await Promise.all([api('/studio/state'),api('/studio/catalog')]);studio.value=s;catalog.value=c.items}
export async function toggleFavorite(id:string){try{const selected=!studio.value.favorites.includes(id);await api('/studio/favorites/'+id,{method:'PUT',body:JSON.stringify({selected})});await loadStudio();notify(selected?'已加入本机收藏':'已取消本机收藏')}catch(e){error.value=e instanceof Error?e.message:'收藏保存失败'}}
export async function saveParameters(extra?:Record<string,unknown>){try{await api('/studio/designs',{method:'POST',body:JSON.stringify({title:draft.value.text||'未命名印章方案',parameters:{...draft.value,customization:extra&&!(extra instanceof Event)?extra:{}},seal_id:latestComposition.value?.seal?.id||null})});await loadStudio();notify('方案已保存到本机作品集')}catch(e){error.value=e instanceof Error?e.message:'方案保存失败'}}
export function validTypeset(text:string){const chars=Array.from(text);return chars.length>=1&&chars.length<=12&&chars.every(c=>{const cp=c.codePointAt(0)!;return cp>=0x3400&&cp<=0x9fff||cp>=0x20000&&cp<=0x323af})}
export async function compose(text?:string){if(making.value)return;const imprint=(text??draft.value.text).trim();if(!validTypeset(imprint)){error.value='实际印文需为1至12个汉字；创作思路可以保留在方案中。';return;}making.value=true;try{const result=await api('/studio/compose',{method:'POST',body:JSON.stringify({text:imprint,creative_prompt:draft.value.text.slice(0,200),layout:draft.value.layout,polarity:draft.value.polarity,ink:draft.value.ink,border:draft.value.border,stroke_px:draft.value.stroke_px,requested_style:draft.value.style,material:draft.value.material})});latestComposition.value=result;draft.value.text=imprint;await refresh();select(result.seal.id);referenceMode.value=false;localStorage.setItem('yinmai-reference-mode','false');await loadStudio();modal.value=null;notify('已完成规范字排版并保存原图。此结果没有使用篆刻风格模型。');return result}catch(e){error.value=e instanceof Error?e.message:'生成失败'}finally{making.value=false}}
export async function shareLink(path:string){try{await navigator.clipboard.writeText(new URL(path,location.origin).href);notify('链接已复制，仅在可访问此本机服务的设备上有效')}catch{show('share','复制作品链接',{url:new URL(path,location.origin).href})}}
