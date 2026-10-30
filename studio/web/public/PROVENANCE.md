# Original demo provenance
The button, servo and articulated character are original procedural designs authored for this repository. No Arduino implementation, private source, external mesh or texture was copied.

The character is a true THREE.SkinnedMesh with seven named bones, rigid skin weights, and two original quaternion clips (Wave, Idle). Its block geometry is deliberately simple so joint behavior and scene transforms remain easy to inspect.

original-character.glb is generated from studio/web/src/assets.ts by studio/web/scripts/generate-demo-glb.mjs, using the locally installed Three.js GLTFExporter. It is a self-contained binary GLTF 2.0 file with no external textures or buffers. The original GLB, procedural designs and scene examples are offered under MIT, matching this repository's original tool code; see LICENSE.txt in this directory. Three.js remains MIT licensed under its package license.
