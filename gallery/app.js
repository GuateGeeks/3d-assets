const $ = (id) => document.getElementById(id);
const viewer = $('viewer');
const pageSize = 24;
const preferred = ['kKtL4zvS3n','QCm7qe9uNJ','4fb-oMr2uUF','a7ZAkNc0F24','P1gU3Qkr9r','05VXLT8kN4k','dwSigTeSMCo','ZUN3itcCyX','8Tke6WIyZtg','2BEJQybmqQT','cf3QwX0JqGN','CA4HtaaMJn'];
const fold = s => String(s ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const collator = new Intl.Collator('es', {sensitivity:'base',numeric:true});
const number = n => new Intl.NumberFormat('es-GT').format(n);
const size = bytes => bytes < 1048576 ? Math.round(bytes/1024)+' KB' : (bytes/1048576).toFixed(1)+' MB';
const state = {area:'',provider:'',kit:'',view:'grouped',license:'',motion:'',sort:'featured',q:'',page:1};
let kits=[],models=[], areas=[], selected=null, matches=[], loadSerial=0, toastTimer;
const aliases = {dog:'perro',cat:'gato',bird:'ave pajaro',frog:'rana',butterfly:'mariposa',turtle:'tortuga',tree:'arbol',flower:'flor flores',plant:'planta',mushroom:'hongo',fish:'pez peces',whale:'ballena',water:'agua',boat:'barco',volcano:'volcan',mountain:'montana',island:'isla',rock:'roca piedra',globe:'globo terraqueo',earth:'tierra',moon:'luna',planet:'planeta',rocket:'cohete',telescope:'telescopio',microscope:'microscopio',brain:'cerebro',heart:'corazon',skeleton:'esqueleto',skull:'craneo',tooth:'diente',corn:'maiz elote',banana:'banano platano',avocado:'aguacate',carrot:'zanahoria',apple:'manzana',cube:'cubo',sphere:'esfera',cone:'cono',dice:'dados dado',ruler:'regla',clock:'reloj',gear:'engranaje',battery:'bateria',computer:'computadora ordenador',keyboard:'teclado',book:'libro',pencil:'lapiz',backpack:'mochila',school:'escuela',desk:'escritorio',house:'casa',traffic:'trafico vial',bridge:'puente',bus:'autobus',bicycle:'bicicleta',car:'carro automovil',train:'tren',airplane:'avion',pyramid:'piramide',temple:'templo',guitar:'guitarra',drum:'tambor bateria',trumpet:'trompeta',paint:'pintura',soccer:'futbol',hammer:'martillo',wrench:'llave herramienta',saw:'sierra',recycle:'reciclaje',trash:'basura',farm:'granja',fence:'cerca',bench:'banca banco',door:'puerta',chest:'cofre',coffee:'cafe',toucan:'tucan',parrot:'loro'};
const flagLabels = {'modular-assembly-piece':'Pieza para ensamblar: puede incluir superficies abiertas o de una sola cara. Revisa uniones, orientación y escala.','adult-beverage-classroom-review':'El kit incluye una bebida de uso adulto; revisar su adecuación a la actividad.','stylized-educational-model':'Representación estilizada; revisar su precisión y escala para la actividad.','gear-mechanics-review':'Engranaje de ilustración: verificar perfil, paso y pivote antes de simular transmisión mecánica.','third-party-animation-mentioned':'La descripción menciona una animación de terceros. Revisa su procedencia.','fantasy-or-combat-classroom-review':'Contenido de fantasía o combate: revisar su adecuación para la actividad.','brand-or-third-party-character-review':'Revisar marcas o personajes de terceros.','anatomy-accuracy-review':'La precisión anatómica necesita revisión docente.','cultural-or-species-identification-review':'Validar la identificación cultural, geográfica o de la especie.','api-animation-metadata-disagrees-with-glb':'El estado de animación del catálogo difiere del archivo. Aquí se usa lo encontrado en el GLB.','unrecognized-license':'La licencia requiere interpretación manual.','requested-object-not-confirmed':'El recurso no acredita uno o más objetos solicitados durante la búsqueda.'};
function el(tag, text, cls) {const node=document.createElement(tag);if(text!=null)node.textContent=text;if(cls)node.className=cls;return node;}
function icon(kind) {
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');
 const p=document.createElementNS(svg.namespaceURI,'path');p.setAttribute('d',kind==='play'?'m9 5 11 7-11 7V5Z':'m12 3 9 5v9l-9 5-9-5V8l9-5Zm0 10v9M3 8l9 5 9-5');svg.append(p);return svg;
}
function notify(message){clearTimeout(toastTimer);$('toast').textContent=message;$('toast').hidden=false;toastTimer=setTimeout(()=>$('toast').hidden=true,2600);}
function url(){
 const hash=new URLSearchParams();if(selected)hash.set('model',selected.id);
 for(const [key,value] of Object.entries(state))if(value&&!(key==='page'&&value===1)&&!(key==='sort'&&value==='featured')&&!(key==='view'&&value==='grouped'))hash.set(key,String(value));
 history.replaceState(null,'','#'+hash.toString());
}
async function copy(text,success){try{await navigator.clipboard.writeText(text);notify(success);}catch{notify('No se pudo copiar. Selecciona el texto y usa Copiar.');}}
function resetCamera(){viewer.cameraOrbit='25deg 75deg 105%';viewer.cameraTarget='auto auto auto';viewer.fieldOfView='auto';viewer.jumpCameraToGoal?.();}
function zoom(factor){if(!viewer.loaded)return;const o=viewer.getCameraOrbit();viewer.cameraOrbit=o.theta+'rad '+o.phi+'rad '+Math.max(.00001,o.radius*factor)+'m';}
function setArea(value){state.area=value;state.page=1;$('area-select').value=value;render();}
function areaNav(){
 const nav=$('areas');nav.replaceChildren();
 for(const a of [{id:'',title:'Todos los modelos'},...areas]){
  const count=a.id?models.filter(m=>m.areas.includes(a.id)).length:models.length;
  const b=el('button',null,'area-button');b.type='button';b.dataset.area=a.id;b.setAttribute('aria-pressed',String(state.area===a.id));
  b.append(el('span',a.title),el('span',number(count),'area-count'));b.addEventListener('click',()=>setArea(a.id));nav.append(b);
 }
}
function sorted(list){
 return [...list].sort((a,b)=>state.sort==='size'?a.bytes-b.bytes||collator.compare(a.title,b.title):state.sort==='name'?collator.compare(a.title,b.title):(preferred.includes(a.id)?preferred.indexOf(a.id):100)-(preferred.includes(b.id)?preferred.indexOf(b.id):100)||collator.compare(a.title,b.title));
}
function render(){
 const terms=fold(state.q).trim().split(/\s+/).filter(Boolean);
 const filtered=sorted(models.filter(m=>(!state.area||m.areas.includes(state.area))&&(!state.provider||m.providerId===state.provider)&&(!state.kit||m.kitIds?.includes(state.kit))&&(!state.license||m.licenseRaw===state.license)&&(!state.motion||(state.motion==='animated'?m.gltf.animated:state.motion==='rigged'?m.gltf.rigged:!m.gltf.animated))&&terms.every(t=>m.searchText.includes(t))));
 const families=new Map();for(const m of filtered){const key=m.variantGroupId||m.id;if(!families.has(key))families.set(key,[]);families.get(key).push(m);}
 for(const members of families.values())for(const m of members)m.visibleVariants=members.length;
 matches=state.view==='grouped'?[...families.values()].map(group=>group.find(m=>m.id===selected?.id)||group[0]):filtered;
 const kit=kits.find(k=>k.id===state.kit);$('kit-download').hidden=!kit;$('kit-download').href=kit?.file||'kits.html';
 const maxPage=Math.max(1,Math.ceil(matches.length/pageSize));state.page=Math.max(1,Math.min(state.page,maxPage));
 const page=matches.slice((state.page-1)*pageSize,state.page*pageSize);const grid=$('grid');grid.replaceChildren();
 for(const m of page){
  const tile=el('button',null,'tile');tile.type='button';tile.dataset.id=m.id;tile.setAttribute('aria-label','Ver en 3D: '+m.title+' · '+m.licenseRaw);tile.setAttribute('aria-pressed',String(selected?.id===m.id));
  const visual=el('span',null,'tile-visual');const img=el('img');img.src='gallery/thumbnails/'+encodeURIComponent(m.id)+'.webp';img.alt='';img.loading='lazy';img.decoding='async';img.width=320;img.height=286;
  img.addEventListener('error',()=>{const fallback=el('span',null,'image-fallback');fallback.append(icon('cube'),el('span','Vista previa no disponible'));visual.replaceChildren(fallback);},{once:true});
  visual.append(img);const meta=el('span',null,'tile-meta');meta.append(el('span',m.licenseRaw));
  if(state.view==='grouped'&&m.visibleVariants>1)meta.append(el('span',m.visibleVariants+' variantes'));
  if(m.gltf.animated){const mark=el('span',null,'motion-mark');mark.append(icon('play'),el('span','Animado'));meta.append(mark);}
  tile.append(visual,el('span',m.title,'tile-title'),meta);tile.addEventListener('click',()=>selectModel(m,true));grid.append(tile);
 }
 $('empty').hidden=matches.length>0;$('grid').hidden=!matches.length;document.querySelector('.pagination').hidden=!matches.length;
 $('results').textContent=matches.length?number(matches.length)+(state.view==='grouped'&&matches.length!==filtered.length?' grupos · '+number(filtered.length)+' modelos':(matches.length===1?' modelo':' modelos'))+(matches.length>pageSize?' · '+number((state.page-1)*pageSize+1)+'–'+number(Math.min(state.page*pageSize,matches.length)):''):'0 modelos';
 $('pages').textContent=state.page+' de '+maxPage;$('prev').disabled=state.page<=1;$('next').disabled=state.page>=maxPage;
 $('clear').hidden=!state.area&&!state.provider&&!state.kit&&!state.license&&!state.motion&&!state.q;document.querySelectorAll('.area-button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.area===state.area)));url();
}
async function selectModel(m,fromTile=false){
 const variants=m.variantGroupId?models.filter(other=>other.variantGroupId===m.variantGroupId):[m];
 $('variant-row').hidden=variants.length<2;$('variant').replaceChildren(...sorted(variants).map(other=>Object.assign(el('option',other.title+' · '+other.provider),{value:other.id})));$('variant').value=m.id;
 selected=m;const serial=++loadSerial;viewer.pause?.();viewer.autoRotate=false;$('rotate').setAttribute('aria-pressed','false');
 $('play').setAttribute('aria-pressed','false');$('play').textContent='Reproducir';$('animation-row').hidden=true;$('viewer-error').hidden=true;$('loading').hidden=false;$('loading').textContent='Cargando vista 3D…';
 $('model-title').textContent=m.title;$('model-author').replaceChildren(document.createTextNode('Por '),Object.assign(el('a',m.author),{href:m.authorUrl,target:'_blank',rel:'noopener'}));
 viewer.alt='Modelo 3D de '+m.title+'. Arrastra o usa las flechas para rotar; usa los controles para acercar.';
 viewer.poster='gallery/thumbnails/'+encodeURIComponent(m.id)+'.webp';resetCamera();viewer.src=m.file;
 $('model-facts').replaceChildren(el('span',size(m.bytes)),el('span',m.gltf.rigged?'Con esqueleto':'Sin esqueleto'),el('span',m.gltf.animations?m.gltf.animations+' clips':'Sin animaciones'));
 $('download').href=m.file;$('download').download=m.title.replace(/[^\p{L}\p{N}_-]/gu,'_')+'.glb';
 $('license-link').textContent=m.licenseRaw;$('license-link').href=m.license.url||'models/'+m.id+'/LICENSE.txt';
 $('license-note').textContent=m.license.attributionRequired===true?'Requiere atribución al autor y enlace a la licencia. Conserva el crédito al usar o compartir el recurso.':m.license.attributionRequired===false?'CC0 no exige atribución de copyright. Conservamos el autor y la procedencia del recurso.':'Revisa el texto original de la licencia antes de usar el recurso.';
 if(m.license.shareAlike)$('license-note').textContent+=' Las adaptaciones deben compartirse bajo la misma licencia. Los archivos originales y las condiciones están conservados en la ficha.';
 $('credit').textContent=m.attribution;$('metadata-link').href=m.sourceMetadataFile;$('source-link').href=m.sourceUrl;$('source-link').textContent='Ver en '+m.provider+' ↗';$('original-link').hidden=!m.originalDownload;$('original-link').href=m.originalDownload||m.file;$('license-evidence').href='models/'+m.id+'/LICENSE.txt';$('description').textContent=m.description||'Sin descripción adicional del autor.';
 $('review-details').hidden=!m.reviewFlags?.length&&!m.unfulfilledQueries?.length;$('review-flags').replaceChildren(...(m.reviewFlags||[]).map(f=>el('li',flagLabels[f]||f)));
 $('unfulfilled').textContent=m.unfulfilledQueries?.length?'Este recurso no confirma: '+m.unfulfilledQueries.join(', ')+'.':'';
 $('technical').replaceChildren();for(const [key,value] of [['ID',m.id],['Fuente',m.provider],['Tamaño',size(m.bytes)],['Mallas',m.gltf.meshes],['Articulaciones',m.gltf.joints],['Animaciones',m.gltf.animations],['Cambios',m.modifications],['SHA-256',m.sha256]])$('technical').append(el('dt',key),el('dd',String(value)));
 document.querySelectorAll('.tile').forEach(tile=>tile.setAttribute('aria-pressed',String(tile.dataset.id===m.id)));url();
 if(fromTile&&matchMedia('(max-width:720px)').matches){$('inspector').focus({preventScroll:true});$('inspector').scrollIntoView({behavior:'instant',block:'start'});}
 try{await customElements.whenDefined('model-viewer');if(serial!==loadSerial)return;if(viewer.loaded)showLoaded();}catch{showError();}
}
function showLoaded(){
 if(!selected)return;$('loading').hidden=true;$('viewer-error').hidden=true;
 const clips=viewer.availableAnimations||[]; const defaultClip=clips.find(name=>/(?:^|[|_])idle$/i.test(name))||clips[0]; $('animation').replaceChildren(...clips.map(name=>Object.assign(el('option',name.split('|').pop()),{value:name}))); if(defaultClip)$('animation').value=defaultClip;
 $('animation-row').hidden=!clips.length;if(clips.length){viewer.animationName=defaultClip;viewer.pause();}viewer.autoRotate=false;
}
function showError(){$('loading').hidden=true;$('viewer-error').hidden=false;$('animation-row').hidden=true;}
viewer.addEventListener('load',showLoaded);viewer.addEventListener('error',showError);
$('zoom-in').addEventListener('click',()=>zoom(.8));$('zoom-out').addEventListener('click',()=>zoom(1.25));$('reset-camera').addEventListener('click',resetCamera);
$('rotate').addEventListener('click',()=>{viewer.autoRotate=!viewer.autoRotate;$('rotate').setAttribute('aria-pressed',String(viewer.autoRotate));});
$('animation').addEventListener('change',()=>{viewer.pause();viewer.animationName=$('animation').value;viewer.currentTime=0;$('play').textContent='Reproducir';$('play').setAttribute('aria-pressed','false');});
$('play').addEventListener('click',()=>{if(viewer.paused){viewer.play();$('play').textContent='Pausar';$('play').setAttribute('aria-pressed','true');}else{viewer.pause();$('play').textContent='Reproducir';$('play').setAttribute('aria-pressed','false');}});
$('retry').addEventListener('click',()=>{if(!selected)return;const m=selected;viewer.removeAttribute('src');requestAnimationFrame(()=>selectModel(m));});
$('variant').addEventListener('change',()=>{const model=models.find(m=>m.id===$('variant').value);if(model){selectModel(model);render();}});
$('copy-credit').addEventListener('click',()=>selected&&copy(selected.attribution,'Atribución copiada'));$('share').addEventListener('click',()=>copy(location.href,'Enlace del modelo copiado'));
let debounce;$('search').addEventListener('input',()=>{clearTimeout(debounce);debounce=setTimeout(()=>{state.q=$('search').value;state.page=1;render();},130);});
for(const key of ['provider','kit','view','license','motion','sort'])$(key).addEventListener('change',()=>{state[key]=$(key).value;state.page=1;render();});
$('area-select').addEventListener('change',()=>setArea($('area-select').value));
function clear(){clearTimeout(debounce);Object.assign(state,{area:'',provider:'',kit:'',view:'grouped',license:'',motion:'',q:'',page:1});$('search').value='';for(const key of ['provider','kit','license','motion'])$(key).value='';$('area-select').value='';$('view').value=state.view;render();}
$('clear').addEventListener('click',clear);$('empty-clear').addEventListener('click',clear);
for(const [id,delta] of [['prev',-1],['next',1]])$(id).addEventListener('click',()=>{state.page+=delta;render();if(matchMedia('(max-width:720px)').matches)$('catalog').scrollIntoView({block:'start'});else $('catalog').scrollTo({top:0});});
document.querySelectorAll('a[href="#catalog"]').forEach(link=>link.addEventListener('click',event=>{event.preventDefault();$('catalog').scrollIntoView({block:'start'});$('catalog').focus({preventScroll:true});}));
document.addEventListener('keydown',e=>{if(e.key==='/'&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('search').focus();}});
async function init(){
 if(location.protocol==='file:')throw new Error('Abre esta galería con el servidor local: python tools/serve_gallery.py. Después entra a http://127.0.0.1:4376/gallery.html');
 const [catalog,plan]=await Promise.all(['index.json','selection.json'].map(async path=>{const response=await fetch(path);if(!response.ok)throw new Error('No se pudo cargar '+path);return response.json();}));
 models=catalog.models;kits=catalog.kits||[];areas=plan.areas;for(const m of models){m.providerId ||= 'poly-pizza';m.provider ||= 'Poly Pizza';}
 const params=new URLSearchParams(location.hash.slice(1));for(const key of ['area','provider','kit','view','license','motion','sort','q'])if(params.has(key))state[key]=params.get(key);state.page=Math.max(1,Number(params.get('page'))||1);
 if(!areas.some(a=>a.id===state.area))state.area='';
 const providers=[...new Map(models.map(m=>[m.providerId,m.provider])).entries()].sort((a,b)=>collator.compare(a[1],b[1]));
 if(!providers.some(([id])=>id===state.provider))state.provider='';
 for(const [id,name] of providers)$('provider').append(Object.assign(el('option',name),{value:id}));
 if(!kits.some(k=>k.id===state.kit))state.kit='';if(!['grouped','all'].includes(state.view))state.view='grouped';
 for(const kit of kits)$('kit').append(Object.assign(el('option',kit.title+' · '+kit.provider),{value:kit.id}));
 const licenses=[...new Set(models.map(m=>m.licenseRaw))].sort();if(!licenses.includes(state.license))state.license='';
 if(!['','animated','rigged','static'].includes(state.motion))state.motion='';if(!['featured','name','size'].includes(state.sort))state.sort='featured';
 for(const a of areas)$('area-select').append(Object.assign(el('option',a.title),{value:a.id}));
 for(const license of licenses)$('license').append(Object.assign(el('option',license),{value:license}));
 for(const key of ['provider','kit','view','license','motion','sort'])$(key).value=state[key];$('area-select').value=state.area;$('search').value=state.q;
 for(const m of models){
  const words=fold(m.title).split(/[^a-z0-9]+/);const translated=Object.entries(aliases).filter(([word])=>words.includes(word)||words.includes(word+'s')).map(([,value])=>value);
  m.searchText=fold([m.title,m.author,m.provider,...m.tags,...m.queries.filter(q=>!m.unfulfilledQueries?.includes(q)),...m.subjects,...m.areas.map(id=>areas.find(a=>a.id===id)?.title||''),...translated].join(' '));
 }
 $('total').textContent=number(models.length)+' modelos para Code Studio y Sócrates · '+areas.length+' áreas';
 areaNav();render();const first=models.find(m=>m.id===params.get('model'))||models.find(m=>m.id===preferred[0])||models[0];if(first)selectModel(first);
}
init().catch(error=>{$('fatal').hidden=false;$('fatal').textContent=error.message;$('total').textContent='No se pudo abrir el catálogo';$('loading').hidden=true;});

