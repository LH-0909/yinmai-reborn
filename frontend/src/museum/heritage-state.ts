import {ref} from 'vue'
import {api} from '../store'
import type {MuseumRecord} from '../graph/seal-domain'
export interface PublishedRecord extends MuseumRecord {preview_available:boolean;impression_available:boolean}
export interface BibliographyEntry {id:string;title:string;kind:string;author_as_listed:string;publication_as_listed:string;date_as_listed:string;url:string;access_state:string;full_text_read:boolean;notice:string}
export interface HeritageOverview {counts:{catalogue_records:number;local_photos:number;local_impressions:number;institutions:number;period_labels:number;period_groups:number;named_seal_makers:number;bibliography_citations:number;bibliography_full_texts_read:number;source_receipts:number;period_disagreements:number};by_period_group:Record<string,number>;institutions:Record<string,number>;featured:PublishedRecord[];bibliography:BibliographyEntry[];notice:string}
export const heritageOverview=ref<HeritageOverview|null>(null),heritageBusy=ref(false),heritageProblem=ref('')
let pending:Promise<void>|undefined
export function loadHeritage(){
 if(pending)return pending
 pending=(async()=>{heritageBusy.value=true;heritageProblem.value='';try{heritageOverview.value=await api<HeritageOverview>('/heritage/overview')}catch(e){heritageOverview.value=null;heritageProblem.value=e instanceof Error?e.message:'来源资料暂不可用'}finally{heritageBusy.value=false;pending=undefined}})()
 return pending
}
