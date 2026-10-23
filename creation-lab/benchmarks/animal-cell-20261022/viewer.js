'use strict';
const $ = id => document.getElementById(id);
const cell = $('cell');
const homeOrbit = '36.87deg 53.74deg 0.75m';
let benchmark = null;
let current = null;
let loadGeneration = 0;
let modelState = 'empty';
let activeModelUrl = null;
const modelErrorMessage = 'No se pudo abrir el modelo 3D. Puedes consultar la vista previa y los archivos.';

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}
function number(value, digits = 0) {
  return typeof value === 'number' && Number.isFinite(value)
    ? value.toLocaleString('es-GT', {maximumFractionDigits: digits}) : '—';
}
function localUrl(value) {
  return typeof value === 'string' && /^\/assets\/[A-F]\/[A-Za-z0-9_-]+\/(?:asset\.glb|source\.blend|renders\/[a-z-]+\.png)$/.test(value) ? value : null;
}
function linkDownload(id, url) {
  const anchor = $(id);
  const safe = localUrl(url);
  if (safe) anchor.setAttribute('href', safe);
  else anchor.removeAttribute('href');
  anchor.setAttribute('aria-disabled', String(!safe));
}
function resetView() {
  cell.cameraTarget = '0m 0m 0m';
  cell.cameraOrbit = homeOrbit;
  cell.fieldOfView = '35deg';
}
function usablePosition(part) {
  return Array.isArray(part.positionGltf) && part.positionGltf.length === 3 &&
    part.positionGltf.every(x => typeof x === 'number' && Number.isFinite(x) && Math.abs(x) < 1);
}
function partsFor(condition) {
  const values = condition.parts && Array.isArray(condition.parts.parts) ? condition.parts.parts : [];
  return benchmark.brief.parts.map(spec => ({...spec, ...values.find(part => part.id === spec.id)}));
}
function selectPart(part, index) {
  $('part-detail').replaceChildren(element('h3', '', `${index + 1}. ${part.label}`), element('p', '', part.function));
  $('parts').querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.part === part.id)));
  cell.querySelectorAll('.hotspot').forEach(button => {
    const active = button.dataset.part === part.id;
    button.classList.toggle('selected', active);
    button.setAttribute('aria-pressed', String(active));
  });
  if (usablePosition(part) && current.urlGlb) {
    // Keep the whole 30 cm model in frame while directing attention to a part.
    // A small target shift avoids cropping the far edge of the cell.
    const target = part.positionGltf.map(value => (value * 0.25).toFixed(5) + 'm').join(' ');
    cell.cameraTarget = target;
    cell.cameraOrbit = homeOrbit;
  }
}
function renderParts(condition) {
  $('parts').replaceChildren();
  cell.querySelectorAll('.hotspot').forEach(node => node.remove());
  partsFor(condition).forEach((part, index) => {
    const item = element('li');
    const button = element('button');
    button.type = 'button';
    button.dataset.part = part.id;
    button.setAttribute('aria-pressed', 'false');
    button.append(element('span', 'part-number', index + 1), element('span', '', part.label));
    button.addEventListener('click', () => selectPart(part, index));
    item.append(button);
    $('parts').append(item);
    if (!usablePosition(part) || !condition.urlGlb) return;
    const spot = element('button', 'hotspot', index + 1);
    spot.type = 'button';
    spot.slot = `hotspot-${index}`;
    spot.dataset.part = part.id;
    spot.dataset.position = part.positionGltf.map(x => `${x}m`).join(' ');
    spot.dataset.visibilityAttribute = 'visible';
    spot.setAttribute('aria-label', `${index + 1}. ${part.label}`);
    spot.setAttribute('aria-pressed', 'false');
    spot.append(element('span', 'hotspot-label', part.label));
    spot.addEventListener('click', () => selectPart(part, index));
    cell.append(spot);
  });
}
function selectCondition(condition) {
  current = condition;
  $('variants').querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.id === condition.id)));
  $('comparison-body').querySelectorAll('tr').forEach(row => row.classList.toggle('selected', row.dataset.id === condition.id));
  $('variant-title').textContent = `Variante ${condition.id} · ${condition.model} / ${condition.reasoningEffort}`;
  $('technical').textContent = condition.runId ? `QA técnica: ${condition.technical}` : 'Pendiente';
  $('technical').classList.toggle('fail', condition.technical === 'FAIL');
  $('review-status').textContent = `Visual: ${reviewStatus(condition.review, 'visual')} · Biología: ${reviewStatus(condition.review, 'biological')}`;
  $('review-summary').textContent = condition.review && typeof condition.review.summary === 'string' && condition.review.summary.trim()
    ? condition.review.summary : 'Revisión educativa pendiente.';
  $('part-detail').replaceChildren(element('h3', '', 'Explora el modelo'), element('p', '', 'Selecciona una estructura para conocer su función y ubicarla en la maqueta.'));
  linkDownload('download-glb', condition.urlGlb);
  linkDownload('download-blend', condition.urlBlend);
  renderParts(condition);
  const modelUrl = localUrl(condition.urlGlb);
  const previewUrl = localUrl(condition.urlPreview);
  $('load-state').hidden = false;
  if (previewUrl) cell.setAttribute('poster', previewUrl);
  else cell.removeAttribute('poster');
  if (modelUrl) {
    // Lit's src property need not reflect to the HTML attribute.
    const sameModel = activeModelUrl === modelUrl;
    if (sameModel && modelState === 'error') {
      $('load-state').textContent = modelErrorMessage;
    } else if (sameModel && (modelState === 'loaded' || cell.loaded)) {
      modelState = 'loaded';
      $('load-state').hidden = true;
    } else {
      modelState = 'loading';
      $('load-state').textContent = 'Cargando modelo 3D…';
      // Reassigning an unchanged src does not emit another load event.
      if (!sameModel) {
        activeModelUrl = modelUrl;
        cell.src = modelUrl;
      }
    }
  } else {
    modelState = 'empty';
    activeModelUrl = null;
    cell.src = null;
    $('load-state').textContent = 'Esta variante todavía no tiene un modelo disponible.';
  }
  resetView();
}
function renderVariants() {
  $('variants').replaceChildren();
  benchmark.conditions.forEach(condition => {
    const button = element('button', 'variant');
    button.type = 'button';
    button.dataset.id = condition.id;
    button.setAttribute('aria-pressed', 'false');
    button.setAttribute('aria-label', `Variante ${condition.id}, ${condition.model}, razonamiento ${condition.reasoningEffort}`);
    const previewUrl = localUrl(condition.urlPreview);
    if (previewUrl) {
      const img = element('img');
      img.src = previewUrl;
      img.alt = '';
      img.loading = 'lazy';
      button.append(img);
    } else button.append(element('span', 'preview-placeholder', condition.id));
    const copy = element('span', 'variant-copy');
    copy.append(element('strong', '', condition.id), element('small', '', condition.model), element('small', '', condition.reasoningEffort), element('small', 'variant-state', condition.runId ? `QA ${condition.technical}` : 'Pendiente'));
    button.append(copy);
    button.addEventListener('click', () => selectCondition(condition));
    $('variants').append(button);
  });
}
function reviewStatus(review, field) {
  if (!review || typeof review !== 'object') return 'Pendiente';
  const status = review[field];
  return typeof status === 'string' ? status : 'Pendiente';
}
function renderComparison() {
  $('comparison-body').replaceChildren();
  benchmark.conditions.forEach(condition => {
    const row = element('tr');
    row.dataset.id = condition.id;
    const metrics = condition.metrics || {};
    const review = condition.review;
    const score = review && typeof review.score === 'number' && Number.isFinite(review.score) ? number(review.score, 1) : '—';
    const values = [condition.id, condition.model, condition.reasoningEffort, number(metrics.triangles), number(metrics.materials), condition.glbBytes === null ? '—' : number(condition.glbBytes / 1048576, 2), condition.seconds === null ? '—' : `${number(condition.seconds, 1)} s`, condition.runId ? condition.technical : 'Pendiente', reviewStatus(review, 'visual'), reviewStatus(review, 'biological'), score];
    values.forEach(value => row.append(element('td', '', value)));
    if (review && typeof review.summary === 'string') row.title = review.summary;
    $('comparison-body').append(row);
  });
}
async function refresh() {
  const generation = ++loadGeneration;
  const button = $('refresh');
  button.disabled = true;
  $('error').hidden = true;
  try {
    const response = await fetch('/api/benchmark', {cache: 'no-store'});
    if (!response.ok) throw new Error('No fue posible leer los resultados locales.');
    const data = await response.json();
    if (!Array.isArray(data.conditions) || !data.brief || !Array.isArray(data.brief.parts)) throw new Error('El informe local no tiene el formato esperado.');
    if (generation !== loadGeneration) return;
    const priorId = current && current.id;
    benchmark = data;
    renderVariants();
    renderComparison();
    const next = benchmark.conditions.find(condition => condition.id === priorId) || chooseInitialCondition(benchmark.conditions);
    if (next) selectCondition(next);
  } catch (error) {
    $('error').textContent = error instanceof Error ? error.message : 'No fue posible cargar el benchmark.';
    $('error').hidden = false;
    if (!benchmark) $('load-state').textContent = 'Resultados no disponibles.';
  } finally { button.disabled = false; }
}
function chooseInitialCondition(conditions) {
  const scored = conditions.filter(condition => condition.technical === 'PASS' && condition.review &&
    condition.review.visual === 'PASS' && condition.review.biological === 'PASS' &&
    typeof condition.review.score === 'number' && Number.isFinite(condition.review.score));
  return scored.reduce((best, condition) => !best || condition.review.score > best.review.score ? condition : best, null) ||
    conditions.find(condition => condition.technical === 'PASS' && condition.urlGlb) ||
    conditions.find(condition => condition.urlGlb) || conditions[0];
}
cell.addEventListener('load', () => { modelState = 'loaded'; $('load-state').hidden = true; resetView(); });
cell.addEventListener('error', () => {
  modelState = 'error';
  $('load-state').textContent = modelErrorMessage;
  $('load-state').hidden = false;
});
$('reset').addEventListener('click', () => {
  resetView();
  $('parts').querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', 'false'));
  cell.querySelectorAll('.hotspot').forEach(button => { button.classList.remove('selected'); button.setAttribute('aria-pressed', 'false'); });
  $('part-detail').replaceChildren(element('h3', '', 'Vista completa'), element('p', '', 'Gira la célula o selecciona una estructura para seguir explorando.'));
});
$('labels').addEventListener('change', event => cell.classList.toggle('hide-labels', !event.target.checked));
$('refresh').addEventListener('click', refresh);
// Avoid setting component properties before the local module registers its
// accessors: early own properties would otherwise shadow model-viewer's API.
customElements.whenDefined('model-viewer').then(refresh);
