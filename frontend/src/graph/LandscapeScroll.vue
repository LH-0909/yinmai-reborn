<script setup lang="ts">
import {ref,onMounted,onBeforeUnmount,watch} from 'vue'
import {IconArrowDown,IconPlayerPause,IconPlayerPlay,IconRefresh,IconArrowUpRight} from '@tabler/icons-vue'
import * as THREE from 'three'
const props=defineProps<{records:number}>()
const emit=defineEmits<{enter:[]}>()
const canvasHost=ref<HTMLElement>(),root=ref<HTMLElement>(),phase=ref('loading'),paused=ref(false),position=ref(32),sourceOpen=ref(false),fallback=ref(false),reduce=ref(false)
let replayScene=()=>{},updateScene=()=>{},cleanup=()=>{}
function replay(){paused.value=false;replayScene()}
function browse(){paused.value=true;updateScene()}
watch(paused,()=>updateScene())
onMounted(()=>{
 const host=canvasHost.value;if(!host)return
 const media=matchMedia('(prefers-reduced-motion: reduce)');reduce.value=media.matches;paused.value=media.matches
 let renderer:THREE.WebGLRenderer|undefined,disposed=false,raf=0,visible=true,last=0,elapsed=media.matches?5.6:0,drift=0,opening=media.matches?1:0,ready=false,pointerX=0,pointerY=0,texture:THREE.Texture|undefined
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(38,1,.1,100),group=new THREE.Group(),geometry=new THREE.PlaneGeometry(1,1,96,20)
 const materials:THREE.Material[]=[],geometries:THREE.BufferGeometry[]=[geometry]
 const paperMat=new THREE.MeshBasicMaterial({color:0xffffff,side:THREE.DoubleSide,toneMapped:false,transparent:true});materials.push(paperMat)
 const paper=new THREE.Mesh(geometry,paperMat);group.add(paper)
 const mountMat=new THREE.MeshStandardMaterial({color:0xc6ad76,roughness:.85,metalness:.1,side:THREE.DoubleSide});materials.push(mountMat)
 const mountGeo=new THREE.PlaneGeometry(1,1),mount=new THREE.Mesh(mountGeo,mountMat);geometries.push(mountGeo);group.add(mount);mount.position.z=-.12
 const woodMat=new THREE.MeshStandardMaterial({color:0x382b1b,roughness:.42,metalness:.2}),goldMat=new THREE.MeshStandardMaterial({color:0xbfa373,roughness:.32,metalness:.75}),silkMat=new THREE.MeshStandardMaterial({color:0xd5bf86,roughness:.85,metalness:.02});materials.push(woodMat,goldMat,silkMat)
 const rolls=[-1,1].map(side=>{
  const g=new THREE.Group();g.userData.side=side
  for(const [radius,height,y,material] of [[.15,5.5,0,silkMat],[.105,.48,-2.98,woodMat],[.105,.48,2.98,woodMat],[.17,.13,-3.2,goldMat],[.17,.13,3.2,goldMat]] as const){const geo=new THREE.CylinderGeometry(radius,radius,height,40);geometries.push(geo);const mesh=new THREE.Mesh(geo,material);mesh.position.y=y;g.add(mesh)}
  group.add(g);return g
 })
 scene.add(group);scene.add(new THREE.HemisphereLight(0xc7ece1,0x34322b,2.7));const key=new THREE.DirectionalLight(0xffe7af,4);key.position.set(-3,5,7);scene.add(key)
 const glow=new THREE.PointLight(0x83c7b2,18,22,2);glow.position.set(3,-1,4);scene.add(glow)
 const dustGeo=new THREE.BufferGeometry(),dust=new Float32Array(110*3)
 for(let i=0;i<110;i++){dust[i*3]=Math.sin(i*128.71)*12;dust[i*3+1]=Math.cos(i*91.31)*6;dust[i*3+2]=-2+Math.sin(i*33.47)*2}
 dustGeo.setAttribute('position',new THREE.BufferAttribute(dust,3));geometries.push(dustGeo)
 const dustMat=new THREE.PointsMaterial({color:0xdfdbb7,size:.018,transparent:true,opacity:.45,depthWrite:false});materials.push(dustMat);const motes=new THREE.Points(dustGeo,dustMat);scene.add(motes)
 function draw(){
  if(!renderer||disposed||!ready)return
  const mobile=host!.clientWidth<800,available=2*12.8*Math.tan(19*Math.PI/180)*camera.aspect,span=mobile?Math.min(7.7,available*.87):Math.min(12.8,2*14.3*Math.tan(19*Math.PI/180)*camera.aspect*.82),height=mobile?Math.min(3.1,span*.65):Math.min(5.05,span*.6),ease=(1-Math.cos(opening*Math.PI))/2,width=.06+span*ease
  const attr=geometry.getAttribute('position') as THREE.BufferAttribute,uv=geometry.getAttribute('uv') as THREE.BufferAttribute
  for(let i=0;i<attr.count;i++){const x=(uv.getX(i)-.5)*width,y=(uv.getY(i)-.5)*height,z=.06*Math.sin(x*.8+drift*.2)*Math.cos(y*.5)+.2*Math.pow(Math.abs(x)/(span/2),8)*(1-ease);attr.setXYZ(i,x,y,z)}
  attr.needsUpdate=true;paperMat.opacity=.12+.88*ease;mount.scale.set(width+.18,height+.24,1)
  for(const roll of rolls){roll.position.x=roll.userData.side*(width/2+.03);roll.scale.y=height/5.05;roll.rotation.y=roll.userData.side*ease*13}
  const windowSize=(span/height)/(39974/1600)
  if(texture){texture.repeat.set(windowSize*ease,1);texture.offset.set(.04+position.value/100*(.9-windowSize)+(1-ease)*windowSize/2,0)}
  group.rotation.set(-.035+pointerY*.015,-.1+pointerX*.025+Math.sin(drift*.15)*.006,-.015);group.position.set(mobile?0:.25,mobile?-0.1:-.8,0)
  camera.position.set(0,mobile?0.55:1.45,mobile?12.8:14.9-.6*ease);camera.lookAt(0,mobile?0:-.25,0)
  motes.rotation.z=drift*.004;renderer.render(scene,camera)
 }
 function frame(now:number){raf=0;if(disposed)return;const delta=last?Math.min(1,(now-last)/1000):0;last=now
  if(visible&&!document.hidden&&!paused.value&&ready){elapsed+=delta;drift+=delta;opening=Math.min(1,elapsed/5.6);if(opening===1&&phase.value!=='open')phase.value='open';if(opening===1&&Math.floor(drift*5)!==Math.floor((drift-delta)*5))position.value=32+Math.sin((drift-5.6)*.035)*27;draw()}
  if(!paused.value&&visible&&!document.hidden)raf=requestAnimationFrame(frame)
 }
 function resize(){if(!renderer||disposed)return;const w=host!.clientWidth,h=host!.clientHeight;camera.aspect=w/Math.max(1,h);camera.updateProjectionMatrix();renderer.setSize(w,h);draw()}
 function fail(){if(disposed)return;fallback.value=true;phase.value='fallback';paused.value=true;cancelAnimationFrame(raf);renderer?.dispose()}
 const lost=(e:Event)=>{e.preventDefault();fail()},move=(e:PointerEvent)=>{const box=host!.getBoundingClientRect();pointerX=(e.clientX-box.left)/box.width-.5;pointerY=(e.clientY-box.top)/box.height-.5;if(paused.value)draw()},resetPointer=()=>{pointerX=0;pointerY=0;if(paused.value)draw()}
 const observer=new ResizeObserver(resize),visibility=new IntersectionObserver(entries=>{visible=entries[0]?.isIntersecting??false;last=0;if(visible&&!paused.value&&!raf)raf=requestAnimationFrame(frame)},{threshold:.03})
 const tabVisibility=()=>{last=0;if(!document.hidden&&visible&&!paused.value&&!raf)raf=requestAnimationFrame(frame)}
 document.addEventListener('visibilitychange',tabVisibility)
 const motionChange=()=>{reduce.value=media.matches;paused.value=media.matches;opening=1;elapsed=5.6;phase.value='open';draw();if(!raf)raf=requestAnimationFrame(frame)}
 replayScene=()=>{if(fallback.value)return;elapsed=0;opening=0;drift=0;phase.value='opening';last=0;draw();if(!raf)raf=requestAnimationFrame(frame)}
 updateScene=()=>{draw();if(!raf&&!paused.value){last=0;raf=requestAnimationFrame(frame)}}
 try{
  renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'low-power'});renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.9
  renderer.domElement.setAttribute('aria-hidden','true');host.appendChild(renderer.domElement);renderer.domElement.addEventListener('webglcontextlost',lost)
  host.addEventListener('pointermove',move);host.addEventListener('pointerleave',resetPointer);observer.observe(host);visibility.observe(root.value!);media.addEventListener('change',motionChange)
  const mobile=host.clientWidth<650||renderer.capabilities.maxTextureSize<16384
  new THREE.TextureLoader().load('/assets/landscape/'+(mobile?'qianli-panorama-mobile.webp':'qianli-panorama.webp'),map=>{if(disposed||fallback.value){map.dispose();return}texture=map;map.colorSpace=THREE.SRGBColorSpace;map.wrapS=THREE.ClampToEdgeWrapping;map.wrapT=THREE.ClampToEdgeWrapping;map.anisotropy=Math.min(4,renderer!.capabilities.getMaxAnisotropy());paperMat.map=map;paperMat.needsUpdate=true;ready=true;phase.value=media.matches?'open':'opening';resize();raf=requestAnimationFrame(frame)},undefined,fail)
  resize()
 }catch{fail()}
 cleanup=()=>{disposed=true;cancelAnimationFrame(raf);observer.disconnect();visibility.disconnect();media.removeEventListener('change',motionChange);document.removeEventListener('visibilitychange',tabVisibility);host.removeEventListener('pointermove',move);host.removeEventListener('pointerleave',resetPointer);renderer?.domElement.removeEventListener('webglcontextlost',lost);texture?.dispose();for(const g of geometries)g.dispose();for(const m of materials)m.dispose();renderer?.dispose();renderer?.domElement.remove()}
})
onBeforeUnmount(()=>cleanup())
</script>

<template>
<section ref="root" class="landscape-scroll" :data-phase="phase" aria-label="千里江山动态画卷">
 <div class="landscape-atmosphere" aria-hidden="true"><img src="/assets/landscape/qianli-detail-official.jpg" alt=""></div>
 <div class="landscape-copy"><span>印脉重生 · 青绿入境</span><h1>一卷江山<span>印见千年</span></h1><p>山川缓缓铺开，方寸自有天地。</p></div>
 <span class="landscape-vertical">展一卷青绿　入万象印境</span>
 <div ref="canvasHost" class="landscape-canvas" role="img" aria-label="千里江山图数字摹本的立体卷轴展开与局部巡游；不是文物三维复原"></div>
 <div v-if="fallback" class="landscape-static"><img src="/assets/landscape/qianli-detail-official.jpg" alt="故宫博物院王希孟千里江山图卷官方局部图"><p>静态赏画 · 可直接进入读印</p></div>
 <button class="landscape-skip" @click="emit('enter')">直接读印 <IconArrowDown :size="14"/></button>
 <div class="landscape-bottom"><div class="landscape-actions"><button class="landscape-enter" @click="emit('enter')">入卷，寻一方印 <IconArrowDown :size="19"/></button><span>{{records||'—'}} 条官方馆藏记录 · 有据可查</span></div><div class="landscape-transport"><label v-if="!fallback">循卷观山<input v-model.number="position" type="range" min="0" max="100" aria-label="浏览长卷" @input="browse"></label><div v-if="!fallback"><button :aria-label="paused?'播放画卷':'暂停画卷'" :disabled="phase==='loading'" @click="paused=!paused"><IconPlayerPlay v-if="paused" :size="15"/><IconPlayerPause v-else :size="15"/></button><button aria-label="重播画卷" :disabled="phase==='loading'" @click="replay"><IconRefresh :size="15"/></button><span role="status">{{phase==='loading'?'正在展卷…':paused?(phase==='opening'?'展开已暂停':'静观山河'):phase==='opening'?'画卷徐徐展开':'青绿山水 · 循卷游观'}}</span></div></div></div>
 <footer class="landscape-source"><button @click="sourceOpen=!sourceOpen" :aria-expanded="sourceOpen">《千里江山图》· 图像与出处 <IconArrowUpRight :size="11"/></button><div v-if="sourceOpen"><p>北宋 · 王希孟 · 故宫博物院藏 · 新00146004。此处为数字摹本的局部动态展示；卷轴和灯光为展陈设计，不代表原器结构或原画运动。</p><a href="https://www.dpm.org.cn/collection/paint/228354.html" target="_blank" rel="noopener noreferrer">故宫官方条目 ↗</a><a href="https://commons.wikimedia.org/wiki/File:Wang_Ximeng._A_Thousand_Li_of_Rivers_and_Mountains._(Complete,_51,3x1191,5_cm)._1113._Palace_museum,_Beijing.jpg" target="_blank" rel="noopener noreferrer">全卷数字摹本 · Wikimedia Commons ↗</a></div></footer>
</section>
</template>

<style scoped>
.landscape-scroll{position:relative;min-height:740px;height:calc(100svh - 74px);max-height:1100px;margin:0 -32px 24px;overflow:hidden;background:#081a1b;color:#e9dfbf;isolation:isolate;border-bottom:1px solid #456355}.landscape-atmosphere{position:absolute;inset:0;overflow:hidden;z-index:-1;opacity:.19;pointer-events:none}.landscape-atmosphere img{width:100%;height:100%;object-fit:cover;filter:blur(22px) saturate(.8);transform:scale(1.1)}.landscape-canvas{position:absolute;inset:0}.landscape-canvas :deep(canvas){display:block;width:100%;height:100%;touch-action:pan-y}.landscape-copy{position:absolute;left:5%;top:8%;z-index:2;pointer-events:none}.landscape-copy>span{font:11px system-ui;letter-spacing:6px;color:#8cbaaa}.landscape-copy h1{font:64px/1.25 MuseumSong,SimSun,serif;font-weight:400;letter-spacing:9px;color:#eee3bc;margin:18px 0 12px;text-shadow:0 2px 25px #001f22}.landscape-copy h1 span{display:inline;margin-left:22px;color:#c9ddc0}.landscape-copy p{font:13px system-ui;letter-spacing:4px;color:#99b2a3}.landscape-vertical{position:absolute;right:5%;top:27%;writing-mode:vertical-rl;font:13px/2.5 MuseumSong,SimSun,serif;letter-spacing:5px;color:#a9c0a9;z-index:2;pointer-events:none}.landscape-scroll .landscape-skip{position:absolute;right:5%;top:7%;display:flex;align-items:center;gap:12px;font:11px system-ui;color:#adc7b7;border-bottom:1px solid #557767;padding-bottom:7px;z-index:3}.landscape-bottom{position:absolute;left:5%;right:5%;bottom:10%;display:flex;justify-content:space-between;align-items:flex-end;z-index:3;gap:24px}.landscape-actions{display:flex;align-items:center;gap:24px}.landscape-scroll .landscape-enter{display:flex;align-items:center;gap:35px;border:1px solid #a9b895;background:#173d38b8;color:#ede4c5;padding:15px 24px;font:17px MuseumSong,SimSun,serif;letter-spacing:3px;transition:background .25s,transform .25s}.landscape-scroll .landscape-enter:hover{background:#305d4e;transform:translateY(-3px)}.landscape-actions>span{font:10px system-ui;letter-spacing:1px;color:#8ba99b}.landscape-transport{width:210px;font:10px system-ui;color:#9eb4a0}.landscape-transport label{display:flex;gap:12px;align-items:center;margin-bottom:13px;white-space:nowrap}.landscape-transport input{width:135px;accent-color:#c3cda6;height:3px;cursor:ew-resize}.landscape-transport>div{display:flex;align-items:center;gap:16px}.landscape-transport button{display:flex;padding:5px!important;border:1px solid #53796a!important}.landscape-transport>div>span{font-size:9px}.landscape-source{position:absolute;bottom:3%;left:5%;right:5%;z-index:4;font:9px/1.8 system-ui;color:#779a89}.landscape-source>button{display:flex;align-items:center;gap:7px;font-size:9px!important}.landscape-source>div{position:absolute;bottom:28px;width:min(420px,100%);padding:18px;background:#132a23f5;border:1px solid #526e50;color:#a5bbaa;box-shadow:0 15px 50px #0008}.landscape-source a{display:block;margin-top:8px;color:#d0d7b1}.landscape-static{position:absolute;inset:31% 12% 25%;display:grid;place-content:center}.landscape-static img{max-width:100%;max-height:380px;width:100%;object-fit:contain}.landscape-static p{font:10px system-ui;text-align:center;color:#9cb19b;margin-top:10px}
@media(max-width:700px){.landscape-scroll{margin:0 -12px 22px;min-height:670px;height:calc(100svh - 62px);max-height:850px}.landscape-copy{left:7%;top:8%}.landscape-copy>span{font-size:9px;letter-spacing:4px}.landscape-copy h1{font-size:43px;letter-spacing:6px;line-height:1.25;margin:17px 0 12px}.landscape-copy h1 span{display:block;margin:0 0 0 40px}.landscape-copy p{font-size:10px;letter-spacing:2px}.landscape-vertical{display:none}.landscape-scroll .landscape-skip{top:4%;right:6%;font-size:9px}.landscape-bottom{bottom:12%;left:7%;right:7%;align-items:flex-start;flex-direction:column;gap:18px}.landscape-actions{gap:13px;align-items:flex-start;flex-direction:column}.landscape-scroll .landscape-enter{padding:12px 20px;font-size:15px}.landscape-actions>span{font-size:9px}.landscape-transport{width:100%;display:flex;justify-content:space-between;align-items:center;gap:12px}.landscape-transport label{margin:0;font-size:9px;gap:7px}.landscape-transport input{width:72px;height:24px}.landscape-transport button{min-width:36px;min-height:36px;justify-content:center}.landscape-transport>div{gap:10px}.landscape-transport>div>span{display:none}.landscape-source{bottom:4%;left:7%;right:7%;font-size:8px}.landscape-static{inset:34% 8% 38%}.landscape-static img{max-height:240px}}
@media(prefers-reduced-motion:reduce){.landscape-enter{transition:none!important}}
</style>
