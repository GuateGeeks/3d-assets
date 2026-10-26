// Samples the cotizador pose vocabulary (asesor/lab/campus-people.js) into keyframed clips.
//   node sample_poses.mjs <cotizador-root> <poses.json> <out.json> [current|original]
// `current` samples POSES as the campus plays it (clips already retouched included);
// `original` samples the pose functions themselves (POSE_FUNCTIONS), the reference for edits.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [root, specFile, out, mode = 'current'] = process.argv.slice(2);
if (!root || !specFile || !out) { console.error('Uso: node sample_poses.mjs <cotizador> <poses.json> <out.json> [current|original]'); process.exit(2); }
const people = await import(pathToFileURL(path.join(root, 'asesor/lab/campus-people.js')).href);
const table = mode === 'original' ? people.POSE_FUNCTIONS : people.POSES;
const spec = JSON.parse(fs.readFileSync(specFile, 'utf8'));
const KEYS = Object.keys(people.pose());

export const clipKey = c => c.args.some(a => typeof a === 'string' && a !== '$t') ? `${c.name}(${c.args.filter(a => a !== '$t').join(',')})` : c.name;

const clips = {};
for (const c of spec.clips) {
  if (!table[c.name]) throw new Error(`POSES.${c.name} no existe en el cotizador`);
  const fps = c.long ? spec.longFps : spec.fps, count = c.time ? Math.max(2, Math.round(c.duration * fps)) : 1;
  const frames = [];
  for (let i = 0; i < count; i++) {
    const t = c.time ? i * c.duration / count : 0;
    const args = c.args.map(a => a === '$t' ? t * c.time.scale : a);
    const p = table[c.name](...args);
    frames.push(Object.fromEntries(KEYS.map(k => [k, Array.isArray(p[k]) ? p[k].map(v => Math.round(v * 1e5) / 1e5) : Math.round((p[k] || 0) * 1e5) / 1e5])));
  }
  clips[clipKey(c)] = { name: c.name, args: c.args, time: c.time || null, offset: c.offset || null, duration: c.duration || 0, fps: c.time ? fps : 0, frames };
}
fs.writeFileSync(out, JSON.stringify({ mode, keys: KEYS, clips }));
console.log(JSON.stringify({ out, mode, clips: Object.keys(clips).length }));
