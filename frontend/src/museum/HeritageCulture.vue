<script setup lang="ts">
import {computed,ref} from 'vue'
import {IconArrowRight,IconChevronLeft,IconChevronRight,IconExternalLink,IconX,IconBook2,IconDatabase,IconHierarchy2} from '@tabler/icons-vue'
import Rect from './Rect.vue'
import Art from './Art.vue'
import registry from '../graph/museum-seals.json'
import type {MuseumRecord} from '../graph/seal-domain'
import {heritageOverview,heritageProblem,heritageBusy,loadHeritage} from './heritage-state'

const sources=[
 {name:'故宫博物院',url:'https://www.dpm.org.cn/collection/seals.html'},
 {name:'中国国家博物馆',url:'https://www.chnmuseum.cn/zp/'},
 {name:'南越王博物院',url:'https://www.nywmuseum.org.cn/Collection/Details/?nid=47'}
]
const groups=computed(()=>Object.entries(heritageOverview.value?.by_period_group||{}))
const primaryPeriods=['战国','秦','西汉','东汉','唐','北宋','明','清','近现代']
const eras=computed(()=>primaryPeriods.filter(name=>heritageOverview.value?.by_period_group[name]).map(name=>({
 name,count:heritageOverview.value!.by_period_group[name],
 record:(Object.values(registry) as MuseumRecord[]).find(r=>!r.period_conflict&&r.display_url&&(name==='近现代'?/近现代|民国|现代/.test(r.period):r.period.startsWith(name)))
})))
const periodDialog=ref<HTMLDialogElement|null>(null)
const bookPage=ref(0),bookPageSize=3
const books=computed(()=>heritageOverview.value?.bibliography.slice(bookPage.value*bookPageSize,(bookPage.value+1)*bookPageSize)||[])
const bookPages=computed(()=>Math.ceil((heritageOverview.value?.bibliography.length||0)/bookPageSize))
function closeOnBackdrop(event:MouseEvent){if(event.target===periodDialog.value)periodDialog.value?.close()}
</script>

<template>
<Rect :x="170" :y="0" :w="1502" :h="199" plain class="hc-hero">
 <Art name="culture-hero" alt="文化溯源 · 山水楼阁与概念印章，非馆藏文物照片"/>
 <h1 class="im-sr-only">文化溯源</h1>
</Rect>
<Rect :x="1182" :y="132" :w="470" :h="64" plain class="hc-metrics">
 <div v-for="(label,key) in {catalogue_records:'馆藏记录',institutions:'馆藏机构',source_receipts:'来源凭证',bibliography_citations:'论著目录'}" :key="key"><b>{{heritageOverview?.counts[key]??'—'}}</b><span>{{label}}</span></div>
</Rect>

<Rect :x="183" :y="201" :w="1038" :h="270" title="按馆藏年代寻印" class="hc-panel hc-period-panel" :aria-busy="heritageBusy">
 <header class="hc-heading"><h2>馆藏年代</h2><span>循一方印 · 读有据的历史</span><button class="hc-text-link" @click="periodDialog?.showModal()">全部分期 <IconChevronRight :size="16"/></button></header>
 <p v-if="heritageProblem" class="hc-error" role="alert">{{heritageProblem}} <button class="im-outline" @click="loadHeritage()">重新读取</button></p>
 <p v-else-if="heritageBusy&&!heritageOverview" class="hc-loading" role="status">正在读取馆藏资料…</p>
 <div v-else class="hc-era-row">
  <RouterLink v-for="era in eras" :key="era.name" :to="{path:'/catalog',query:{period:era.name}}" class="hc-era">
   <div class="hc-era-image"><img v-if="era.record" :src="era.record.display_url" :alt="era.record.official_title+' · 官方馆藏图像'"><span v-else>馆藏目录</span></div>
   <b>{{era.name}}</b><span>{{era.count}} <small>条馆藏记录</small></span>
  </RouterLink>
 </div>
 <p class="hc-caption">据馆方年代文字归类 · 组印按一条目录记录计 · 点击年代查阅馆藏</p>
</Rect>

<Rect :x="1230" :y="202" :w="426" :h="275" title="馆藏来源" class="hc-panel hc-source-panel">
 <header class="hc-heading"><h2>馆藏来源</h2><span>每一条，皆有出处</span></header>
 <div class="hc-sources"><a v-for="(source,i) in sources" :key="source.name" :href="source.url" target="_blank" rel="noopener noreferrer"><span class="hc-source-number">0{{i+1}}</span><span><b>{{source.name}}</b><small>官方馆藏目录</small></span><IconExternalLink :size="17"/></a></div>
 <p class="hc-caption">图像保留馆方原貌，可回到原始条目核对。</p>
</Rect>

<Rect :x="183" :y="483" :w="1038" :h="289" title="真实馆藏选读" class="hc-panel hc-object-panel">
 <header class="hc-heading"><h2>方寸之间</h2><span>从真实馆藏，走进古印的知识宇宙</span><RouterLink class="hc-text-link" to="/catalog">全部馆藏 <IconChevronRight :size="16"/></RouterLink></header>
 <div class="hc-objects"><RouterLink v-for="r in heritageOverview?.featured.slice(0,4)" :key="r.node_id" :to="{path:'/graph',query:{node:r.node_id}}" class="hc-object">
  <div class="hc-object-image"><img :src="r.display_url" :alt="r.official_title+' · 官方馆藏图像'" loading="lazy"><span>馆藏实录</span></div>
  <div class="hc-object-copy"><h3>{{r.label}}</h3><p>{{r.period}}</p><small>{{r.museum}}</small><IconArrowRight :size="18"/></div>
 </RouterLink></div>
</Rect>

<Rect :x="1230" :y="486" :w="426" :h="248" title="史料与研究入口" class="hc-panel hc-book-panel">
 <header class="hc-heading"><h2>史料与研究</h2><span>{{heritageOverview?.counts.bibliography_citations??'—'}} 条目录</span></header>
 <p class="hc-book-notice">故宫推荐目录 · 全文尚未核读</p>
 <ol class="hc-books" :start="bookPage*bookPageSize+1"><li v-for="b in books" :key="b.id"><a :href="b.url" target="_blank" rel="noopener noreferrer" :title="b.title"><b>{{b.title}}</b><IconExternalLink :size="13"/><small>{{b.author_as_listed||'目录未列作者'}} · {{b.date_as_listed||b.publication_as_listed}}</small></a></li></ol>
 <div class="hc-book-pagination" aria-label="文献目录分页"><button class="im-round" aria-label="上一页文献" :disabled="bookPage===0" @click="bookPage--"><IconChevronLeft :size="17"/></button><span>{{bookPage+1}} / {{bookPages||1}}</span><button class="im-round" aria-label="下一页文献" :disabled="bookPage+1>=bookPages" @click="bookPage++"><IconChevronRight :size="17"/></button></div>
</Rect>

<Rect :x="183" :y="780" :w="610" :h="145" title="循印读史" class="hc-panel hc-path-panel">
 <header class="hc-heading"><h2>循印读史</h2><span>实物 · 印文 · 有据关系</span></header>
 <div class="hc-reading-path">
  <RouterLink to="/catalog"><IconDatabase :size="25"/><span><b>寻一方印</b><small>阅览官方馆藏</small></span><IconChevronRight :size="14"/></RouterLink>
  <RouterLink :to="{path:'/graph',query:{node:heritageOverview?.featured[0]?.node_id}}"><IconHierarchy2 :size="25"/><span><b>读印中天地</b><small>查看印文与出处</small></span><IconChevronRight :size="14"/></RouterLink>
  <button @click="periodDialog?.showModal()"><IconBook2 :size="25"/><span><b>观时代流转</b><small>按来源分期寻印</small></span><IconChevronRight :size="14"/></button>
 </div>
</Rect>

<Rect :x="804" :y="780" :w="418" :h="145" title="山河入卷" class="hc-panel hc-scroll-panel">
 <RouterLink class="hc-scroll-link" to="/graph"><img src="/assets/landscape/qianli-panorama-mobile.webp" alt="《千里江山图》数字图像局部" loading="lazy"><div><h2>山河入卷</h2><p>赏千里江山，入古印天地</p><span>展开画卷 <IconArrowRight :size="17"/></span></div></RouterLink>
</Rect>

<Rect :x="1230" :y="742" :w="426" :h="183" title="来源分期待核对" class="hc-panel hc-review-panel">
 <header class="hc-heading"><h2>史料辨读</h2><RouterLink class="hc-text-link" :to="{path:'/catalog',query:{period:'分期待核对'}}">查看条目 <IconChevronRight :size="16"/></RouterLink></header>
 <p class="hc-review-count"><b>{{heritageOverview?.counts.period_disagreements??'—'}}</b> 条来源分期不同</p><p class="hc-review-text">目录与正文的分期说法并列保留。<br>核对前，不建立确定的年代关系。</p>
</Rect>

<dialog ref="periodDialog" class="hc-period-dialog" aria-labelledby="hc-period-title" @click="closeOnBackdrop">
 <header class="hc-heading"><h2 id="hc-period-title">按来源分期寻印</h2><button class="im-round" aria-label="关闭全部分期" @click="periodDialog?.close()"><IconX :size="19"/></button></header>
 <p>数量为本系统已接入的目录记录，组印按一条记录计。</p>
 <div class="hc-period-options"><RouterLink v-for="[name,count] in groups" :key="name" :to="{path:'/catalog',query:{period:name}}" @click="periodDialog?.close()"><span>{{name}}</span><b>{{count}} <small>条</small></b><IconChevronRight :size="15"/></RouterLink></div>
 <p class="hc-dialog-note">来源分期不同的条目单列，保留原始说法供核对。</p>
</dialog>
</template>

<style scoped>
/* Use the reference artwork, engraved frames and shared MuseumSong typeface. */
.hc-panel{color:#d5c9ad;font-size:15px}
.hc-panel .hc-heading{display:flex;align-items:center;gap:15px;min-height:36px;border-bottom:1px solid #6b51334d;padding:0 7px 8px;margin-bottom:10px}
.hc-heading h2{font-size:23px;line-height:1.15;white-space:nowrap;font-weight:500;letter-spacing:2px}
.hc-heading>span{color:#aa9674;font-size:13px;letter-spacing:1px}
.hc-heading .hc-text-link{margin-left:auto;display:inline-flex;align-items:center;gap:4px;color:#ddc08a;font-size:13px;white-space:nowrap}
.hc-caption{color:#ab9c81;font-size:12px;letter-spacing:.5px}
.hc-metrics{display:grid;grid-template-columns:repeat(4,1fr);align-items:center;padding:2px 0;background:#090908c9}
.hc-metrics>div{text-align:center;border-left:1px solid #77603f5c}.hc-metrics>div:first-child{border:0}
.hc-metrics b{font-size:27px;font-weight:400;color:#f4d397;line-height:1.2;display:block}
.hc-metrics span{font-size:14px;letter-spacing:1px;color:#c4baa3}
.hc-era-row{display:grid;grid-template-columns:repeat(9,minmax(0,1fr));gap:10px;padding:0 5px;margin:1px 0 10px}
.hc-era{min-width:0;text-align:center;transition:transform .25s}.hc-era:hover{transform:translateY(-3px)}
.hc-era-image{height:105px;border:1px solid #765c3a;background:#12100d url('/assets/museum/field-texture.png');padding:5px;overflow:hidden}
.hc-era-image img{width:100%;height:100%;object-fit:contain;display:block}
.hc-era-image>span{display:flex;align-items:center;justify-content:center;height:100%;color:#a99676;font-size:12px}
.hc-era>b{display:block;font-size:19px;font-weight:400;color:#f2d9ab;letter-spacing:2px;margin-top:7px}
.hc-era>span{font-size:17px;color:#dfbd7f}.hc-era small{font-size:11px;color:#a99c83}
.hc-period-panel>.hc-caption{padding-left:5px}
.hc-sources>a{display:flex;align-items:center;gap:13px;border-bottom:1px solid #654f333d;padding:6px 7px}.hc-sources>a:last-child{border:0}
.hc-source-number{font-size:24px;color:#99794b;width:29px}
.hc-sources b{display:block;font-size:17px;font-weight:400;color:#e4c99a;letter-spacing:1px}
.hc-sources small{display:block;color:#a99c83;font-size:12px}.hc-sources>a>svg{margin-left:auto;color:#b39a70}
.hc-source-panel>.hc-caption{padding:4px 7px}
.hc-objects{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;padding:0 5px}
.hc-object{min-width:0;border:1px solid #82623c;display:block;background:#0c0b09 url('/assets/museum/field-texture.png');transition:border-color .2s}
.hc-object:hover{border-color:#e8bd79}
.hc-object-image{height:128px;position:relative;background:#171510;overflow:hidden;border-bottom:1px solid #755b36}
.hc-object-image img{width:100%;height:100%;object-fit:contain;display:block}
.hc-object-image>span{position:absolute;bottom:5px;left:7px;background:#472116eb;border:1px solid #935b3c;color:#ead1a5;font-size:10px;padding:1px 5px}
.hc-object-copy{position:relative;padding:7px 11px}
.hc-object-copy h3{font-size:18px;line-height:1.25;font-weight:400;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#edd1a0}
.hc-object-copy p{font-size:12px;line-height:1.5;color:#b5a68d;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:3px}
.hc-object-copy small{font-size:11px;line-height:1.4;color:#a99a7f}.hc-object-copy>svg{position:absolute;right:10px;bottom:10px;color:#cfb17b}
.hc-book-panel .hc-heading{margin-bottom:3px}.hc-book-panel .hc-heading>span{margin-left:auto}
.hc-book-notice{font-size:12px;color:#b5a081;padding-left:7px}
.hc-books{list-style:none;margin:7px 7px 0;padding:0;height:120px}
.hc-books li{padding:5px 0;border-bottom:1px solid #6c543335;min-width:0}.hc-books li:last-child{border:0}
.hc-books a{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 6px;align-items:center}
.hc-books b{font-size:15px;font-weight:400;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#e6c893}
.hc-books small{font-size:11px;color:#ae9e83;grid-column:1/-1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hc-books svg{color:#a68c61}
.hc-book-pagination{display:flex;align-items:center;justify-content:flex-end;gap:11px;margin:7px 7px 0;font-size:12px;color:#bca47d}
.hc-book-pagination .im-round{width:25px;height:25px}.hc-book-pagination button:disabled{cursor:default;opacity:.3}
.hc-path-panel .hc-heading{margin-bottom:7px}
.hc-reading-path{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));padding:0 5px}
.hc-reading-path>a,.hc-reading-path>button{display:flex;align-items:center;gap:10px;padding:6px 13px;text-align:left;border-right:1px solid #76562f66;min-width:0}
.hc-reading-path>a:first-child{padding-left:0}.hc-reading-path>button:last-child{border:0}.hc-reading-path svg{color:#c5a166}
.hc-reading-path b{font-size:17px;font-weight:400;color:#e6cc9d;display:block;white-space:nowrap}
.hc-reading-path small{display:block;font-size:12px;color:#a89b84;white-space:nowrap;margin-top:4px}
.hc-reading-path span+svg{margin-left:auto}
.hc-scroll-link{position:relative;display:block;height:100%;overflow:hidden;background:#0c0b08}
.hc-scroll-link>img{position:absolute;width:100%;height:100%;object-fit:cover;opacity:.3;object-position:55% center;transition:opacity .5s,transform 1s}
.hc-scroll-link:hover>img{opacity:.5;transform:scale(1.04)}.hc-scroll-link>div{position:relative;padding:6px 13px}
.hc-scroll-link h2{font-size:24px;font-weight:500;letter-spacing:4px}
.hc-scroll-link p{font-size:13px;color:#ccbea5;margin-top:5px}
.hc-scroll-link span{display:flex;align-items:center;gap:9px;font-size:13px;color:#ecc68a;margin-top:12px}
.hc-review-panel .hc-heading{margin-bottom:7px}
.hc-review-count{font-size:15px;letter-spacing:1px;padding-left:7px;color:#d2b68a}
.hc-review-count b{font-size:29px;font-weight:400;color:#edbb6e;margin-right:9px;line-height:1.3}
.hc-review-text{font-size:13px;line-height:1.8;color:#bfb096;padding:4px 7px 0}
.hc-error,.hc-loading{padding:30px;color:#d6bf95;line-height:1.9}
.hc-period-dialog{margin:auto;width:min(720px,calc(100vw - 36px));max-height:85vh;color:#d7c7a7;border:14px solid transparent;border-image:url('/assets/museum/panel-frame.png') 14 fill stretch;background:#0c0b09 url('/assets/museum/surface-texture.png');padding:20px;overflow:auto;font:15px/1.7 MuseumSong,SimSun,serif}
.hc-period-dialog::backdrop{background:#000c}
.hc-period-dialog .hc-heading{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #695332;padding-bottom:15px;margin-bottom:14px}
.hc-period-dialog .hc-heading h2{font-size:24px}.hc-period-dialog p{font-size:13px;color:#b6a68a}
.hc-period-options{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:20px 0}
.hc-period-options>a{display:flex;align-items:center;padding:10px 12px;border:1px solid #705334;background:#15110c;gap:5px}
.hc-period-options b{margin-left:auto;color:#d7b57c;font-weight:400}.hc-period-options small{font-size:11px;color:#a59476}
.hc-dialog-note{padding-top:10px;border-top:1px solid #6c5133}
@media(max-width:999px){
 .hc-panel{flex:none}
 .hc-hero>.im-art{object-fit:cover;object-position:left;height:100%;width:100%}
 .hc-metrics{grid-template-columns:repeat(4,minmax(0,1fr));min-height:65px}
 .hc-metrics b{font-size:23px}.hc-metrics span{font-size:10px;letter-spacing:0}
 .hc-panel .hc-heading{padding:0 2px 10px;gap:9px;flex-wrap:wrap}
 .hc-heading h2{font-size:21px}.hc-heading>span{font-size:11px;letter-spacing:0}.hc-heading .hc-text-link{font-size:12px;min-height:36px}
 .hc-era-row{grid-template-columns:repeat(3,minmax(0,1fr));gap:17px 9px;padding:2px}
 .hc-era-image{height:87px}.hc-era>b{font-size:17px;margin-top:5px}.hc-era>span{font-size:15px}.hc-era small{display:block;font-size:10px}
 .hc-period-panel>.hc-caption{margin-top:15px;font-size:11px;line-height:1.8}
 .hc-sources>a{padding:11px 4px}.hc-sources b{font-size:16px}.hc-sources small{font-size:11px}
 .hc-objects{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px 9px;padding:2px}
 .hc-object-image{height:125px}.hc-object-copy{padding:8px}.hc-object-copy h3{font-size:16px}
 .hc-object-copy p{font-size:11px;line-height:1.7}.hc-object-copy small{font-size:10px}.hc-object-copy>svg{display:none}
 .hc-caption{font-size:11px;line-height:1.8}
 .hc-books{height:auto;margin:12px 2px}.hc-books li{padding:10px 0}.hc-books b{font-size:15px}.hc-books small{font-size:11px}
 .hc-book-notice{font-size:11px;padding-left:2px}.hc-book-pagination{margin:12px 2px 4px}.hc-book-pagination .im-round{width:44px;height:44px}
 .hc-reading-path{grid-template-columns:1fr}.hc-reading-path>a,.hc-reading-path>button{padding:13px 2px;border-right:0;border-bottom:1px solid #76562f55}
 .hc-reading-path b{font-size:17px}.hc-reading-path small{font-size:12px}
 .hc-scroll-link{min-height:130px}.hc-scroll-link>div{padding:12px 8px}.hc-review-text{font-size:13px;padding-bottom:6px}
 .hc-period-dialog{padding:12px;border-width:10px}.hc-period-options{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
 .hc-period-options>a{padding:10px 8px;font-size:13px}.hc-period-dialog .hc-heading h2{font-size:20px}
}
@media(prefers-reduced-motion:reduce){.hc-era,.hc-scroll-link>img{transition:none}.hc-era:hover,.hc-scroll-link:hover>img{transform:none}}
</style>
