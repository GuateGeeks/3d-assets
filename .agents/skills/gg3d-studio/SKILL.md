---
name: gg3d-studio
description: Use when creating interactive objects or animated scenes with code, resuming Meshy or Tripo jobs, importing existing rigs, or choosing between Studio, Blender, UniRig and SkinTokens.
---

# Code-first 3D Studio

Run commands from the repository root. Start with `python studio/studio.py capabilities`
and the [Studio manual](../../../studio/README.md). Configuration, adapter implementation,
connector exposure and real execution are different facts; consult the
[current evidence](../../../studio/docs/STATUS.md).

| Requested work | Route |
| --- | --- |
| Interactive code object or scene | [Authoring](../../../studio/docs/AUTHORING.md), original factories, scene JSON and browser preview |
| Meshy / Tripo generation or recovery | [Provider jobs](../../../studio/docs/PROVIDERS.md), `provider --help` |
| Existing rig / clip / Blender edit | [Engines](../../../studio/docs/ENGINES.md), `backend blender inspect`, `export` or `retarget` |
| Reviewed static candidate → UniRig | `backend unirig ingest`, then `rig`, with the existing candidate manifests |
| SkinTokens | Explicit configured executor, pinned profile, memory preflight and separate live receipt |
| Cotizador 12-bone papercraft | [Existing specialization](../gg3d-blender-web/SKILL.md) |

## Interactive object

Use the original button/servo/character examples as executable references, with explicit
units and provenance. New factories are trusted source compiled into the preview; scene
JSON cannot select arbitrary executable modules. Keep root placement under scene control,
local motion under the asset, and one clock. Current playback evaluates analytical poses
at absolute time; it is not a physics simulator. Inspect transformed anchors, cancellation,
keyboard input, reduced motion, repeated disposal and critical animation states.

```sh
python studio/studio.py project init study --scene studio/examples/interactive.scene.json --author GuateGeeks --license MIT
python studio/studio.py validate studio/.local/projects/study/project.json
python studio/studio.py preview --project studio/.local/projects/study
```

Build the preview first as documented. Create a new project/run for a changed source;
preserve the previous input inventory and evidence. A GLB is optional interchange;
executable interaction remains source plus runtime and scene data.

## Real-asset part contracts (micro:bit V2 lessons)

For a GLB whose parts the runtime drives (`behavior: "microbit"`, contract in
`studio/examples/microbit/node-contract.json`), these decisions held up:

- Contract by `extras.part_id`, each id exactly once on a node, one Blender object per
  part, each LED one primitive on a material no other node uses (an exporter that
  merges materials breaks per-LED light). Press caps need unrotated, unscaled
  ancestors. Run `python3 creation-lab/experiments/microbit-v2/check_contract.py GLB`
  before installing; the factory rejects a bad GLB by part name.
- The LED rest look (`ledRest`) and brightness mapping (`ledEmissive`, intensity
  = `maxIntensity * (value/255)^brightnessGamma`) are applied by the factory at load.
  They are not in the GLB, so a lab visual PASS on renders does not cover them.
- Scene fields: `behavior`, `patternBindings` (heart/smile/check stand-ins, not
  simulator output) and an authored `camera` `{elevation, azimuth}`. Centimetre-size
  assets rely on the scale-aware stage (near plane, zoom limits, shadow follow the
  world size); do not rescale the asset to make the viewer cooperate.
- Test the real asset on first contact, not only a synthetic board: the open-ring
  touch logo let a click at its centre fall through to the PCB until the factory
  parented an invisible hit box to it.
- Judge product captures at the viewer's default camera with a fresh blind reviewer.
  The lab renders passing did not mean the interactive product read: two of three
  Studio rounds failed on LED look and default camera before passing.

## Provider recovery

Prepare the exact transport request and persist submission intent before a paid call.
The CLI prepares envelopes; Codex invokes rediscovered MCP tools. Require the scoped
cost authorization described in the provider guide. After a create timeout, use
`provider unknown`, reconcile the existing remote task, then `provider resume`.
Never change a request to bypass duplicate guards. Download, hash and intake the actual
output; fixture tests and a successful account check do not prove generation.

## Rig and animation

Inspect an existing skinned GLB without removing its rig. The static UniRig intake is
not that route. Cross-skeleton motion needs an explicit supported map/rest pose;
Meshy animation requires its own rig task ID. A shared file format is not skeleton
compatibility. Current Blender retargeting rejects differing rest axes rather than
silently repairing them. SkinTokens remains unavailable on insufficient memory.

Use [shared gates](../../../studio/docs/ACCEPTANCE.md): technical, visual, content and
provenance. Open actual images before visual verdicts. Packages require reviews bound
to exact artifact hashes; local output never promotes itself to the public catalog.
