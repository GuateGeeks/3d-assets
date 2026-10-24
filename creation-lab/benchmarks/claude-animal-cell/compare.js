'use strict';
const $ = id => document.getElementById(id);
const cell = $('cell');
const homeOrbit = '36.87deg 53.74deg 0.75m';
let data = null;
let current = null;
let activeModelUrl = null;

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
  return typeof value === 'string' && /^\/(?:gpt\/assets\/[A-F]|claude\/R\d+)\/[A-Za-z0-9_-]+\/(?:asset\.glb|source\.blend|renders\/[a-z-]+\.png)$/.test(value) ? value : null;
}
const key = condition => `${condition.family}:${condition.id}`;
function status(review, field) {
  return review && typeof review[field] === 'string' ? review[field] : 'Pendiente';
}
function score(review) {
  return review && typeof review.score === 'number' && Number.isFinite(review.score) ? review.score : null;
}
function fullPass(condition) {
  return condition.technical === 'PASS' && status(condition.review, 'visual') === 'PASS' &&
    status(condition.review, 'biological') === 'PASS' && (condition.family === 'GPT' || condition.stage === 'detail');
}
function pending(condition) {
  // Claude replicas still iterating are not final failures.
  return condition.family === 'Claude' && !fullPass(condition) && (!condition.review || condition.stage !== 'detail');
}
function stateClass(value) {
  return value === 'PASS' ? 'pass' : value === 'FAIL' || value === 'BLOCKED' ? 'fail' : '';
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
  return data.brief.parts.map(spec => ({...spec, ...values.find(part => part.id === spec.id)}));
}
function selectPart(part, index) {
  $('part-detail').replaceChildren(element('h3', '', `${index + 1}. ${part.label}`), element('p', '', part.function));
  $('parts').querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.part === part.id)));
  cell.querySelectorAll('.hotspot').forEach(button => button.classList.toggle('selected', button.dataset.part === part.id));
  if (usablePosition(part) && current.urlGlb) {
    cell.cameraTarget = part.positionGltf.map(value => (value * 0.25).toFixed(5) + 'm').join(' ');
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
    spot.append(element('span', 'hotspot-label', part.label));
    spot.addEventListener('click', () => selectPart(part, index));
    cell.append(spot);
  });
}
function selectCondition(condition) {
  current = condition;
  document.querySelectorAll('.variant').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.key === key(condition))));
  $('comparison-body').querySelectorAll('tr').forEach(row => row.classList.toggle('selected', row.dataset.key === key(condition)));
  const stage = condition.family === 'Claude' && condition.stage ? ` · ${condition.stage}` : '';
  $('variant-title').textContent = `${condition.family} ${condition.id} · ${condition.model || '—'} / ${condition.reasoningEffort || '—'}${stage}`;
  $('technical').textContent = condition.runId ? `QA técnica: ${condition.technical}` : 'Pendiente';
  $('technical').classList.toggle('fail', condition.technical === 'FAIL');
  const value = score(condition.review);
  $('review-status').textContent = `Visual: ${status(condition.review, 'visual')} · Biología: ${status(condition.review, 'biological')}${value === null ? '' : ` · Score ${value}/100`}`;
  $('review-summary').textContent = condition.review && condition.review.summary ? condition.review.summary : 'Revisión ciega pendiente para este run.';
  $('part-detail').replaceChildren(element('h3', '', 'Explora el modelo'), element('p', '', 'Selecciona una estructura para conocer su función y ubicarla en la maqueta.'));
  linkDownload('download-glb', condition.urlGlb);
  linkDownload('download-blend', condition.urlBlend);
  renderParts(condition);
  const modelUrl = localUrl(condition.urlGlb);
  const previewUrl = localUrl(condition.urlPreview);
  if (previewUrl) cell.setAttribute('poster', previewUrl);
  else cell.removeAttribute('poster');
  $('load-state').hidden = false;
  if (modelUrl && modelUrl !== activeModelUrl) {
    $('load-state').textContent = 'Cargando modelo 3D…';
    activeModelUrl = modelUrl;
    cell.src = modelUrl;
  } else if (modelUrl) {
    $('load-state').hidden = true;
  } else {
    activeModelUrl = null;
    cell.src = null;
    $('load-state').textContent = 'Esta variante todavía no tiene un modelo disponible.';
  }
  resetView();
}
function renderGroups() {
  $('groups').replaceChildren();
  data.groups.forEach(group => {
    const section = element('section', 'group');
    const heading = element('div', 'group-heading');
    heading.append(element('h2', '', group.title), element('p', '', group.note));
    const nav = element('nav', 'variants');
    nav.setAttribute('aria-label', group.title);
    group.conditions.forEach(condition => {
      const button = element('button', 'variant');
      button.type = 'button';
      button.dataset.key = key(condition);
      button.setAttribute('aria-pressed', 'false');
      const previewUrl = localUrl(condition.urlPreview);
      if (previewUrl) {
        const img = element('img');
        img.src = previewUrl;
        img.alt = '';
        img.loading = 'lazy';
        button.append(img);
      } else button.append(element('span', 'preview-placeholder', condition.id));
      const copy = element('span', 'variant-copy');
      const verdict = fullPass(condition) ? ['pass', `PASS · ${number(score(condition.review))}`]
        : pending(condition) ? ['', condition.stage ? `${condition.stage} · en curso` : 'Pendiente'] : ['fail', 'No aprobado'];
      copy.append(element('strong', '', condition.id), element('small', '', condition.model || '—'), element('small', '', condition.reasoningEffort || '—'), element('span', `badge ${verdict[0]}`, verdict[1]));
      button.append(copy);
      button.addEventListener('click', () => selectCondition(condition));
      nav.append(button);
    });
    section.append(heading, nav);
    $('groups').append(section);
  });
}
function renderSummary() {
  const rows = new Map();
  data.groups.forEach(group => group.conditions.forEach(condition => {
    const id = `${condition.family}|${condition.model}|${condition.reasoningEffort}`;
    if (!rows.has(id)) rows.set(id, {family: condition.family, model: condition.model, effort: condition.reasoningEffort, items: []});
    rows.get(id).items.push(condition);
  }));
  $('summary-body').replaceChildren();
  [...rows.values()].forEach(row => {
    const scores = row.items.map(c => score(c.review)).filter(v => v !== null);
    const best = scores.length ? Math.max(...scores) : null;
    const mean = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null;
    const tr = element('tr');
    [row.family, row.model || '—', row.effort || '—', row.items.length, `${row.items.filter(fullPass).length} / ${row.items.length}`,
      row.items.filter(pending).length, number(best), number(mean, 1)].forEach(v => tr.append(element('td', '', v)));
    $('summary-body').append(tr);
  });
}
function renderComparison() {
  $('comparison-body').replaceChildren();
  data.groups.forEach(group => {
    const head = element('tr', 'group-row');
    const td = element('td', '', group.title);
    td.colSpan = 12;
    head.append(td);
    $('comparison-body').append(head);
    group.conditions.forEach(condition => {
      const row = element('tr');
      row.dataset.key = key(condition);
      const metrics = condition.metrics || {};
      const review = condition.review;
      const iterations = condition.runId ? `${condition.iterations} ${condition.iterationKind[condition.iterations === 1 ? 0 : 1]}` : '—';
      const cells = [condition.id, condition.model || '—', condition.reasoningEffort || '—', condition.stage || '—', iterations,
        number(metrics.triangles), number(metrics.materials), condition.glbBytes === null ? '—' : number(condition.glbBytes / 1048576, 2),
        condition.runId ? condition.technical : 'Pendiente', status(review, 'visual'), status(review, 'biological'), number(score(review))];
      cells.forEach((value, index) => row.append(element('td', index >= 8 && index <= 10 ? stateClass(value) : '', value)));
      if (review && review.summary) row.title = review.summary;
      row.addEventListener('click', () => selectCondition(condition));
      $('comparison-body').append(row);
    });
  });
}
async function refresh() {
  const button = $('refresh');
  button.disabled = true;
  $('error').hidden = true;
  try {
    const response = await fetch('/api/compare', {cache: 'no-store'});
    if (!response.ok) throw new Error('No fue posible leer los resultados locales.');
    const next = await response.json();
    if (!Array.isArray(next.groups) || !next.brief || !Array.isArray(next.brief.parts)) throw new Error('El informe local no tiene el formato esperado.');
    const prior = current && key(current);
    data = next;
    renderGroups();
    renderSummary();
    renderComparison();
    const all = data.groups.flatMap(group => group.conditions);
    const best = all.filter(fullPass).reduce((a, c) => !a || score(c.review) > score(a.review) ? c : a, null);
    const chosen = all.find(c => key(c) === prior) || best || all.find(c => c.urlGlb) || all[0];
    if (chosen) selectCondition(chosen);
  } catch (error) {
    $('error').textContent = error instanceof Error ? error.message : 'No fue posible cargar la comparación.';
    $('error').hidden = false;
  } finally { button.disabled = false; }
}
cell.addEventListener('load', () => { $('load-state').hidden = true; resetView(); });
cell.addEventListener('error', () => {
  $('load-state').textContent = 'No se pudo abrir el modelo 3D. Puedes consultar la vista previa y los archivos.';
  $('load-state').hidden = false;
});
$('reset').addEventListener('click', () => {
  resetView();
  $('parts').querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', 'false'));
  cell.querySelectorAll('.hotspot').forEach(button => button.classList.remove('selected'));
});
$('labels').addEventListener('change', event => cell.classList.toggle('hide-labels', !event.target.checked));
$('refresh').addEventListener('click', refresh);
customElements.whenDefined('model-viewer').then(refresh);
