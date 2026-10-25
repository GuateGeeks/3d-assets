import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const viewport = document.querySelector('#viewport');
const status = document.querySelector('#load-state');
const errorBox = document.querySelector('#error');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xfafbfa);
const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.001, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1;
renderer.setClearColor(0xfafbfa, 1);
renderer.domElement.setAttribute('aria-label', 'Modelo 3D; arrastra para orbitar y usa la rueda para acercar');
viewport.append(renderer.domElement);

scene.add(new THREE.HemisphereLight(0xffffff, 0x858b91, 2.0));
const key = new THREE.DirectionalLight(0xffffff, 2.25);
key.position.set(-3, 5, 6);
scene.add(key);
const fill = new THREE.DirectionalLight(0xffffff, 1.1);
fill.position.set(4, 1, -4);
scene.add(fill);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minZoom = 0.35;
controls.maxZoom = 8;
controls.target.set(0, 0, 0);

let model = null;
const originalMaterials = new Map();
let initial = null;
let isClay = false;
let isWireframe = false;
const clayMaterial = new THREE.MeshStandardMaterial({ color: 0xc9ccca, roughness: 0.82, metalness: 0 });

function setStatus(message, kind = '') {
  status.textContent = message;
  status.dataset.kind = kind;
}
function resize() {
  const width = Math.max(1, viewport.clientWidth);
  const height = Math.max(1, viewport.clientHeight);
  const aspect = width / height;
  const half = initial ? Math.max(initial.size.y * 0.56, Math.hypot(initial.size.x, initial.size.z) * 0.56 / aspect) : 0.6;
  camera.left = -half * aspect;
  camera.right = half * aspect;
  camera.top = half;
  camera.bottom = -half;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height, false);
  updateReferenceCrop();
}
function fitModel() {
  const bounds = new THREE.Box3().setFromObject(model);
  const center = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z, 0.0001);
  initial = { center, size, maxDim };
  controls.target.copy(center);
  camera.up.set(0, 1, 0);
  camera.position.set(center.x, center.y, center.z + maxDim * 3);
  camera.zoom = 1;
  camera.near = Math.max(maxDim / 1000, 0.00001);
  camera.far = maxDim * 20;
  camera.lookAt(center);
  camera.updateProjectionMatrix();
  controls.update();
  resize();
}
function setView(name) {
  if (!initial) return;
  const { center, maxDim } = initial;
  const directionByView = { front: [0, 0, 1], 'three-quarter': [1, 0, 1], side: [1, 0, 0], back: [0, 0, -1] };
  const direction = new THREE.Vector3(...(directionByView[name] || directionByView.front)).normalize();
  camera.up.set(0, 1, 0);
  camera.position.copy(center).addScaledVector(direction, maxDim * 3);
  camera.zoom = 1;
  camera.lookAt(center);
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
  updateReferenceCrop();
  document.querySelectorAll('[data-view]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.view === name)));
}
function applyMaterials() {
  if (!model) return;
  model.traverse(object => {
    if (!object.isMesh) return;
    const originals = originalMaterials.get(object);
    if (isClay) {
      object.material = clayMaterial;
    } else if (originals) {
      object.material = originals.wasArray ? originals.materials : originals.materials[0];
    }
    if (isClay) {
      clayMaterial.wireframe = isWireframe;
    } else if (originals) {
      originals.materials.forEach((material, index) => {
        material.wireframe = isWireframe || originals.wireframes[index];
      });
    }
  });
}
function setMaterialModes() {
  isClay = document.querySelector('#clay').checked;
  isWireframe = document.querySelector('#wireframe').checked;
  applyMaterials();
}

document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => setView(button.dataset.view)));
document.querySelector('#reset').addEventListener('click', () => setView('front'));
document.querySelector('#clay').addEventListener('change', setMaterialModes);
document.querySelector('#wireframe').addEventListener('change', setMaterialModes);
const reference = document.querySelector('#reference');
let referenceCrop = 'front';
function updateReferenceCrop() {
  if (referenceCrop !== 'front') {
    reference.style.backgroundSize = 'contain';
    reference.style.backgroundPosition = 'center';
    return;
  }
  const width = reference.clientWidth;
  if (!width || !viewport.clientHeight || !initial) return;
  const desiredHeight = viewport.clientHeight * initial.size.y * camera.zoom / (camera.top - camera.bottom);
  const viewportRect = viewport.getBoundingClientRect();
  const referenceRect = reference.getBoundingClientRect();
  const desiredCenterY = viewportRect.top + viewport.clientHeight / 2 - referenceRect.top;
  const scale = desiredHeight / 658;
  reference.style.backgroundSize = `${1536 * scale}px ${1024 * scale}px`;
  reference.style.backgroundPosition = `${width / 2 - 213 * scale}px ${desiredCenterY - 212 * scale - 329 * scale}px`;
}
document.querySelectorAll('[data-crop]').forEach(button => button.addEventListener('click', () => {
  referenceCrop = button.dataset.crop;
  reference.classList.toggle('is-front', referenceCrop === 'front');
  document.querySelectorAll('[data-crop]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  updateReferenceCrop();
}));
new ResizeObserver(updateReferenceCrop).observe(reference);
updateReferenceCrop();
new ResizeObserver(resize).observe(viewport);

const requestedModel = new URLSearchParams(location.search).get('model');
let modelUrl = '../delivery/model.glb';
let trialRun = '';
if (requestedModel) {
  const candidate = new URL(requestedModel, location.href);
  const match = candidate.pathname.match(/^\/session\/runs\/([^/]+)\/asset\.glb$/);
  if (candidate.origin === location.origin && match) {
    modelUrl = candidate.href;
    trialRun = decodeURIComponent(match[1]);
    setStatus(`Cargando vista de ensayo · ${trialRun}…`);
  } else {
    errorBox.hidden = false;
    errorBox.textContent = 'La ruta de ensayo debe ser local: ../session/runs/<run>/asset.glb.';
    setStatus('Ruta de modelo no permitida', 'error');
  }
} else {
  setStatus('Cargando ../delivery/model.glb…');
}
if (!requestedModel || trialRun) new GLTFLoader().load(modelUrl, gltf => {
  model = gltf.scene;
  model.traverse(object => {
    if (!object.isMesh) return;
    const wasArray = Array.isArray(object.material);
    const materials = wasArray ? object.material : [object.material];
    originalMaterials.set(object, { wasArray, materials, wireframes: materials.map(material => material.wireframe) });
  });
  scene.add(model);
  fitModel();
  setMaterialModes();
  updateReferenceCrop();
  setStatus(trialRun ? `Vista de ensayo · ${trialRun}` : 'Modelo cargado', 'ready');
}, undefined, error => {
  console.error('No se pudo cargar el modelo local', error);
  errorBox.hidden = false;
  errorBox.textContent = trialRun ? `No se pudo cargar la corrida de ensayo ${trialRun}.` : 'No se pudo cargar ../delivery/model.glb. Comprueba que el archivo exista y que abriste este visor mediante el servidor local.';
  setStatus('Error al cargar el modelo', 'error');
});

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();









