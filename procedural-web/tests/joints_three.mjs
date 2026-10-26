// World joint positions of a cotizador student in a few poses (three.js), for the convention test.
//   node joints_three.mjs <cotizador> <model: nino|nina>
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [root, model] = process.argv.slice(2), lab = p => import(pathToFileURL(path.join(root, 'asesor/lab', p)).href);
const { createBuilder } = await lab('campus-kit.js'), { addPaperPerson } = await lab('paper/pieces-people.js'), { POSES, applyPose } = await lab('campus-people.js');
const b = createBuilder(); b.base('solid');
const p = addPaperPerson(b, { id: 'x', level: 'prim', seed: 'prim-b', skirt: model === 'nina' });
b.finish({});
const out = {};
for (const [clip, name, args] of [['highFive(R)', 'highFive', ['R']], ['walk', 'walk', [0, 1]], ['think', 'think', []]]) {
  applyPose(p, POSES[name](...args), 'stand');
  p.root.updateMatrixWorld(true);
  out[clip] = Object.fromEntries(Object.entries(p.joints).map(([k, j]) => [k, j.getWorldPosition(new j.position.constructor()).toArray()]));
}
console.log(JSON.stringify(out));
