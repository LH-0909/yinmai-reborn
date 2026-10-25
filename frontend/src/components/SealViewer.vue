<script setup lang="ts">
import {onMounted,onBeforeUnmount,ref,watch} from 'vue'
import * as THREE from 'three'
import {OrbitControls} from 'three/addons/controls/OrbitControls.js'
import {STLLoader} from 'three/addons/loaders/STLLoader.js'
import {IconRotate,IconFocus2,IconTopologyStar3} from '@tabler/icons-vue'
const props=defineProps<{url?:string;color?:string}>()
const emit=defineEmits<{loaded:[]}>()
const root=ref<HTMLDivElement>();const problem=ref('');const loaded=ref(false);const wire=ref(false)
let renderer:THREE.WebGLRenderer,scene:THREE.Scene,camera:THREE.PerspectiveCamera,controls:OrbitControls,model:THREE.Mesh|undefined,frame=0,observer:ResizeObserver,serial=0
function fit(){
 if(!model||!camera||!controls)return
 const sphere=new THREE.Box3().setFromObject(model).getBoundingSphere(new THREE.Sphere())
 const vertical=THREE.MathUtils.degToRad(camera.fov),horizontal=2*Math.atan(Math.tan(vertical/2)*camera.aspect)
 const distance=sphere.radius/Math.sin(Math.min(vertical,horizontal)/2)*1.12
 controls.target.copy(sphere.center)
 camera.position.copy(sphere.center).add(new THREE.Vector3(1,.85,1.2).normalize().multiplyScalar(distance))
 camera.near=Math.max(.1,distance-sphere.radius*3);camera.far=Math.max(1500,distance+sphere.radius*4);camera.updateProjectionMatrix();controls.update()
}
function reset(){if(model)fit();else{camera?.position.set(46,42,50);controls?.target.set(0,4,0);controls?.update()}}
function load(){if(!scene)return; const n=++serial;loaded.value=false;problem.value=''; if(model){scene.remove(model);model.geometry.dispose();(model.material as THREE.Material).dispose();model=undefined}if(!props.url)return
 new STLLoader().load(props.url,geometry=>{if(n!==serial){geometry.dispose();return}geometry.computeVertexNormals();const mat=new THREE.MeshStandardMaterial({color:props.color||'#a33720',roughness:.38,metalness:.18,wireframe:wire.value});model=new THREE.Mesh(geometry,mat);model.rotation.x=-Math.PI/2;model.castShadow=true;scene.add(model);fit();loaded.value=true;emit('loaded')},undefined,()=>problem.value='模型加载失败，请重新生成或下载文件检查。')}
onMounted(()=>{try{const el=root.value!;renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;el.appendChild(renderer.domElement);renderer.domElement.setAttribute('aria-label','可旋转的真实STL三维印面');scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(40,1,.1,1500);controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;scene.add(new THREE.HemisphereLight('#fff0cb','#382521',3));const light=new THREE.DirectionalLight('#ffddb1',4);light.position.set(20,60,40);scene.add(light);const fill=new THREE.DirectionalLight('#f28c41',2);fill.position.set(-40,10,-30);scene.add(fill);scene.add(new THREE.GridHelper(120,24,'#674021','#322018'));reset();observer=new ResizeObserver(()=>{const {width,height}=el.getBoundingClientRect();if(!width||!height)return;renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();fit()});observer.observe(el);const render=()=>{frame=requestAnimationFrame(render);controls.update();renderer.render(scene,camera)};render();load()}catch{problem.value='此设备暂不支持WebGL，可直接下载STL。'}})
watch(()=>props.url,load);watch(()=>props.color,c=>{if(model)(model.material as THREE.MeshStandardMaterial).color.set(c||'#a33720')})
function toggle(){wire.value=!wire.value;if(model)(model.material as THREE.MeshStandardMaterial).wireframe=wire.value}
onBeforeUnmount(()=>{serial++;cancelAnimationFrame(frame);observer?.disconnect();controls?.dispose();scene?.traverse(obj=>{if(obj instanceof THREE.Mesh){obj.geometry.dispose();(obj.material as THREE.Material).dispose()}});renderer?.dispose()})
</script>
<template><div class="model-view"><div ref="root" class="webgl"></div><div v-if="!url&&!problem" class="model-empty"><h3>等待生成三维印面</h3><p>选择印谱并生成模型，即可旋转查看真实STL。</p></div><div v-if="url&&!loaded&&!problem" class="model-empty">正在读取STL网格…</div><div v-if="problem" class="model-empty">{{problem}}</div><div class="model-tools"><button @click="reset" title="重置视角"><IconRotate/>重置</button><button @click="toggle" title="显示线框"><IconTopologyStar3/>线框</button><button @click="reset" title="适应画布"><IconFocus2/>居中</button></div><span class="view-caption">鼠标旋转 · 滚轮缩放 · 单位 mm</span></div></template>
