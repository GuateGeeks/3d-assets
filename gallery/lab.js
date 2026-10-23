// Local review extends the catalog. Static hosting does not request laboratory data.
const requested = new URLSearchParams(location.search).get('lab') === '1';
const local = ['127.0.0.1', 'localhost', '[::1]'].includes(location.hostname);
const $ = id => document.getElementById(id);
let manifest, asset, syncing = false;
const option = (value, label) => Object.assign(document.createElement('option'), {value, textContent: label});
function mount() {
 const main = document.createElement('main'); main.id = 'lab-review'; main.hidden = true; main.tabIndex = -1; document.querySelector('.skip').href='#lab-review'; document.querySelector('.skip').textContent='Ir a la revisión';
 main.innerHTML = `
 <div class="lab-heading"><div><h1>Revisa el rig antes de animar</h1><p>Compara el control original con UniRig en poses estáticas de diagnóstico.</p></div><a class="secondary" href="gallery.html">Volver a la biblioteca</a></div>
 <div class="lab-controls">
 <label>Modelo<select id="lab-asset"></select></label>
 <label>Prueba de deformación<select id="lab-pose"></select></label>
 <label>Referencia<select id="lab-reference"><option value="control">Rig original</option><option value="prepared">Entrada sin rig · reposo</option></select></label>
 <label class="lab-check"><input type="checkbox" id="lab-bones">Ver esqueleto</label>
 <label class="lab-check"><input type="checkbox" id="lab-sync" checked>Vincular cámaras</label>
 <button class="secondary" id="lab-reset" type="button">Restablecer vista</button>
 </div>
 <p id="lab-pose-note" class="lab-caption"></p><p id="lab-pose-metrics" class="lab-caption" aria-live="polite"></p>
 <div class="lab-comparison">
 <section aria-labelledby="lab-left-title"><div class="lab-view-heading"><h2 id="lab-left-title">Rig original</h2><span id="lab-left-meta"></span></div><div class="lab-stage"><model-viewer id="lab-left" camera-controls touch-action="pan-y" interaction-prompt="none" environment-image="neutral" shadow-intensity="0.5" loading="eager"><div slot="progress-bar"></div></model-viewer><p class="lab-load" id="lab-left-load" role="status">Cargando referencia…</p></div></section>
 <section aria-labelledby="lab-right-title"><div class="lab-view-heading"><h2 id="lab-right-title">UniRig · candidato</h2><span id="lab-right-meta"></span></div><div class="lab-stage"><model-viewer id="lab-right" camera-controls touch-action="pan-y" interaction-prompt="none" environment-image="neutral" shadow-intensity="0.5" loading="eager"><div slot="progress-bar"></div></model-viewer><p class="lab-load" id="lab-right-load" role="status">Cargando candidato…</p></div></section>
 </div>
 <p class="lab-caption">Arrastra para rotar; desplaza o pellizca para acercar. Las poses aplican el mismo giro en ejes globales a articulaciones equivalentes. Los pivotes de cada rig pueden diferir.</p>
 <div class="lab-evidence"><section><h2>Resultado de la ejecución</h2><p id="lab-run"></p><dl id="lab-metrics"></dl><p id="lab-observations"></p><details><summary>Procedencia y modificaciones</summary><p id="lab-credit"></p><a id="lab-source" target="_blank" rel="noopener">Fuente original</a><p id="lab-changes"></p><p id="lab-hashes"></p></details><a id="lab-download" class="text-button" download>Descargar candidato GLB</a></section>
 <form id="lab-form"><h2>Revisión de deformaciones</h2><p>Comprueba cada pose desde el frente y el perfil. El pase técnico no aprueba la calidad visual.</p><label class="lab-check"><input type="checkbox" name="volume">Volumen en hombros, codos y rodillas</label><label class="lab-check"><input type="checkbox" name="symmetry">Simetría y separación de extremidades</label><label class="lab-check"><input type="checkbox" name="drag">Sin arrastre de torso, cara o patas vecinas</label><label>Dictamen<select name="verdict"><option value="pending">Pendiente de revisión</option><option value="changes">Necesita correcciones</option><option value="ready">Apto para preparar clips</option></select></label><label>Observaciones<textarea name="notes" rows="3" placeholder="Pose, zona afectada y corrección propuesta…"></textarea></label><div class="lab-save"><button class="primary" type="submit">Exportar revisión JSON</button><span id="lab-saved" role="status">Notas guardadas en este navegador.</span></div></form></div>`;
 document.querySelector('.workspace').after(main);
 for (const side of ['left','right']) {
  const viewer=$('lab-'+side);
  viewer.addEventListener('load',()=>{if(viewer.src.endsWith(viewer.dataset.expected)) $('lab-'+side+'-load').hidden=true;});
  viewer.addEventListener('error',()=>{const label=$('lab-'+side+'-load');label.hidden=false;label.textContent='No se pudo cargar la vista. Cambia de pose o recarga la página.';});
  viewer.addEventListener('camera-change',e=>{
   if (syncing || !$('lab-sync').checked || e.detail.source !== 'user-interaction') return;
   const other=$('lab-'+(side==='left'?'right':'left'));syncing=true;
   const orbit=viewer.getCameraOrbit(), target=viewer.getCameraTarget();
   other.cameraOrbit=`${orbit.theta}rad ${orbit.phi}rad ${orbit.radius}m`;
   other.cameraTarget=`${target.x}m ${target.y}m ${target.z}m`;other.fieldOfView=`${viewer.getFieldOfView()}deg`;other.jumpCameraToGoal();syncing=false;
  });
 }
 $('lab-asset').addEventListener('change',selectAsset);
 for (const id of ['lab-pose','lab-reference','lab-bones']) $(id).addEventListener('change',loadPose);
 $('lab-reset').addEventListener('click',resetCameras);
 $('lab-sync').addEventListener('change',()=>{if($('lab-sync').checked)resetCameras();});
 $('lab-form').addEventListener('input',saveNotes);
 $('lab-form').addEventListener('submit',event=>{
  event.preventDefault();const report={schemaVersion:1,asset:asset.id,runId:asset.runId,reviewRunId:asset.reviewRunId,mappingSha256:asset.mappingSha256,sourceSha256:asset.sourceSha256,candidateSha256:asset.candidateSha256,pose:$('lab-pose').value,recordedAt:new Date().toISOString(),...formValue()};
  const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)+'\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`rig-review-${asset.id}-${asset.runId}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  $('lab-saved').textContent='Revisión exportada. El candidato conserva su estado hasta incorporar el dictamen al laboratorio.';
 });
}
function key(){return 'rig-review:'+asset.id+':'+asset.runId+':'+asset.reviewRunId;}
function formValue(){const f=$('lab-form');return {volume:f.elements.volume.checked,symmetry:f.elements.symmetry.checked,drag:f.elements.drag.checked,verdict:f.elements.verdict.value,notes:f.elements.notes.value};}
function saveNotes(){try{localStorage.setItem(key(),JSON.stringify(formValue()));$('lab-saved').textContent='Notas guardadas en este navegador.';}catch{$('lab-saved').textContent='No se pudieron guardar las notas; exporta la revisión.';}}
function selectAsset(){
 asset=manifest.assets.find(a=>a.id===$('lab-asset').value);
 $('lab-pose').replaceChildren(...asset.poses.map(p=>option(p.id,p.label)));
 $('lab-run').textContent=`${asset.runId} · ${asset.seconds.toFixed(1)} s · Semilla ${asset.seed} · ${asset.reviewStatus}`;
 $('lab-metrics').replaceChildren();
 for(const [label,value] of [['Articulaciones',asset.bones],['Vértices con pesos',asset.weightedVertices],['Sin peso / sin normalizar',`${asset.unweightedVertices} / ${asset.badWeights}`],['Clips nuevos',0]]){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;$('lab-metrics').append(dt,dd);}
 $('lab-observations').textContent=asset.observations.join(' ');
 $('lab-credit').textContent=asset.attribution;$('lab-source').href=asset.sourceUrl;
 $('lab-changes').textContent=asset.modifications.join('; ');
 $('lab-hashes').textContent=`SHA-256 original: ${asset.sourceSha256} · candidato: ${asset.candidateSha256}`;
 $('lab-download').href=asset.candidateUrl;
 const form=$('lab-form');form.reset();
 try{const saved=JSON.parse(localStorage.getItem(key())||'null');if(saved){for(const name of ['volume','symmetry','drag'])form.elements[name].checked=!!saved[name];form.elements.verdict.value=saved.verdict;form.elements.notes.value=saved.notes;}}catch{/* Notes are optional; the report remains exportable. */}
 $('lab-saved').textContent='Notas de esta ejecución guardadas en este navegador.';
 resetCameras();loadPose();
}
function resetCameras(){
 if(!asset)return;
 const [theta,phi,radius]=asset.cameraOrbit.split(' ');
 for(const side of ['left','right']){
  const v=$('lab-'+side),aspect=v.clientWidth/Math.max(1,v.clientHeight);
  v.cameraOrbit=`${theta} ${phi} ${parseFloat(radius)*Math.max(1,1.4/aspect)}m`;
  v.cameraTarget=asset.cameraTarget;v.fieldOfView='30deg';v.jumpCameraToGoal();
 }
}
matchMedia('(max-width:720px)').addEventListener('change',resetCameras);
function loadPose(){
 const pose=asset.poses.find(p=>p.id===$('lab-pose').value),bones=$('lab-bones').checked,prepared=$('lab-reference').value==='prepared';
 $('lab-pose-note').textContent=pose.description;
 const metric=pose.metrics;
 $('lab-pose-metrics').textContent=metric?`Estiramiento máximo de arista (>2 mm): control ${metric.control.maximumEdgeStretch.toFixed(2)}× · UniRig ${metric.candidate.maximumEdgeStretch.toFixed(2)}×. Es un indicador local, no una calificación visual.`:'';
 $('lab-left-title').textContent=prepared?'Entrada sin rig · reposo':'Rig original · control';
 $('lab-left-meta').textContent=prepared?'Sin articulaciones':asset.controlBones+' articulaciones';$('lab-right-meta').textContent=asset.bones+' articulaciones';
 for(const [side,url] of [['left',prepared?asset.preparedUrl:pose.control[bones?'skeleton':'mesh']],['right',pose.candidate[bones?'skeleton':'mesh']]]){
  const v=$('lab-'+side),message=$('lab-'+side+'-load');v.alt=`${asset.label}: ${side==='left'?'referencia':'UniRig'}, ${pose.label}${bones?', esqueleto':''}`;
  if(v.dataset.expected!==url){message.textContent='Cargando vista 3D…';message.hidden=false;v.dataset.expected=url;v.src=url;}
 }
}
async function init(){
 if(!local && !requested)return;
 if(requested){mount();document.body.classList.add('lab-mode');$('lab-review').hidden=false;$('lab-review').setAttribute('aria-busy','true');document.title='Revisión de rigging · GuateGeeks';}
 try{
  if(!local)throw new Error('La revisión requiere el servidor local con --lab.');
  const response=await fetch('_lab/manifest.json',{cache:'no-store'});if(!response.ok)throw new Error('Prepara la revisión y abre el servidor con python3 tools/serve_gallery.py --lab.');manifest=await response.json();
  if(!manifest.assets?.length)throw new Error('Todavía no hay candidatos. Ejecuta prepare, rig y review antes de abrir esta vista.');
  $('lab-link').hidden=false;if(!requested)return;
  await customElements.whenDefined('model-viewer');$('lab-asset').replaceChildren(...manifest.assets.map(a=>option(a.id,a.label)));selectAsset();$('lab-review').removeAttribute('aria-busy');
 }catch(error){if(requested){$('lab-review').replaceChildren();const p=document.createElement('p');p.className='fatal';p.textContent=error.message;const a=document.createElement('a');a.href='gallery.html';a.textContent='Volver a la biblioteca';$('lab-review').append(p,a);}}
}
init();
