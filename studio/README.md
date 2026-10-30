# 3D Lab Studio

A local, code-first workspace for interactive objects, generated models, rigs and animated scenes. Codex orchestrates the work; a browser previews it; Blender and the existing rigging laboratory remain specialized backends. See [current verification](docs/STATUS.md) and the [approved design](../docs/superpowers/specs/2026-10-29-unified-3d-lab-design.md).

## Start the preview

Use Python >=3.10 and Node >=22.12 (Node 24 is the CI target). WSL/Linux is recommended for the existing UniRig and SkinTokens executors. From the repository root:

```sh
npm ci --prefix studio/web
npm run build --prefix studio/web
python3 studio/studio.py doctor
python3 studio/studio.py project init workbench --scene studio/examples/interactive.scene.json --brief studio/examples/workbench.brief.json --author GuateGeeks --license MIT
python3 studio/studio.py preview --project studio/.local/projects/workbench --port 4395
```

Open http://127.0.0.1:4395/?scene=project/scene.json. Select the button, servo or original articulated character; inspect controls, clips, anchors, bounds and rigs; play, pause or scrub. View options include loop/speed, reduced-motion override, diagnostics and PNG capture. The preview serves an explicit inventory over loopback. It is an inspection surface, not a full timeline editor.

For the self-contained GLB character example, initialize another project with `--scene studio/examples/character.scene.json`. It includes an original seven-bone skin and two clips. Source and example licenses are [documented](examples/PROVENANCE.md). No private Arduino code or recovered assets are dependencies.

## Choose a route

| Work | Entry point |
| --- | --- |
| Interactive object factories and scenes | [Authoring](docs/AUTHORING.md), `studio/web/src`, `studio/examples` |
| Meshy/Tripo task preparation, receipt intake and resume | [Providers](docs/PROVIDERS.md), `python3 studio/studio.py provider --help` |
| Blender inspection, export and explicit motion transfer | [Engines](docs/ENGINES.md), `backend blender` |
| Existing reviewed static candidate into UniRig | [Engines](docs/ENGINES.md), `backend unirig ingest` / `rig` |
| SkinTokens with eligible local or SSH executor | [Engines](docs/ENGINES.md), `backend skintokens rig` |
| Existing Blender procedural creation | [creation-lab](../creation-lab/START-HERE.md) |
| Cotizador's rigid 12-bone roundtrip | [procedural-web](../procedural-web/README.md) |

`python3 studio/studio.py capabilities` distinguishes implemented routes, configuration and live verification. The MCP adapter prepares tool envelopes and consumes real receipts; the CLI cannot call a connector owned by a chat. Provider fixture tests are not live generation. Paid intent defaults to zero; obtain explicit scoped credit authorization before invoking a paid tool.

## Configuration and preservation

Global options precede the command. Keep per-machine config outside versioned sources:

```sh
mkdir -p studio/.local
cp studio/config.example.json studio/.local/config.json
# Set only the desired backend's real paths using docs/ENGINES.md.
python3 studio/studio.py --config studio/.local/config.json capabilities
python3 studio/studio.py --config studio/.local/config.json backend blender demo
```

Blender accepts `blender.python` (existing bpy Python) or `blender.executable`. UniRig uses `unirig.laboratoryRoot` and `unirig.python` to invoke the existing candidate runner, retaining its locks and scale restoration. SkinTokens has a pinned profile and requires >=14 GiB free NVIDIA memory plus configured dependencies; no GPU rental, installation or download happens automatically. Native Blender and UniRig's bpy environments remain separate.

`studio/.local` holds projects/runs/provider jobs. New runs/events preserve earlier evidence; project IDs cannot be reused. Supply a measurable `--brief` for production work (goal, axes, dimensions, style, budgets, references and rights); without it the project records `briefStatus: NOT_PROVIDED`. Structural validity does not approve a missing brief. To change a scene, edit a source scene and initialize a new project revision. Imported GLB paths must be relative to that scene's folder, self-contained and inventoried. Existing rigs are inspected/preserved; static UniRig intake is not an import path for animated assets.

## Validate and package

```sh
python3 studio/studio.py validate studio/.local/projects/workbench/project.json
python3 studio/studio.py run list
python3 studio/studio.py run show RUN_ID
python3 studio/studio.py package --manifest /path/to/package-manifest.json --output /path/to/new-package.zip
```

[Contracts](contracts/records.schema.json) describe project, asset, rig, motion, scene, run and package records. The Python validator adds cross-field/path/hash checks. Validation of a GLB checks its container and embedded resources; use full glTF, Blender and visual QA before accepting an asset.

Packaging requires explicit reviews bound to the entire file inventory. Read [acceptance](docs/ACCEPTANCE.md) for the review format and separate technical/visual/content/provenance gates. Packages do not publish themselves. The gallery builder excludes Studio, private configs, engine dependencies and runs; deployment stays manual.

## Verify the implementation

```sh
python3 -m unittest discover -s studio/tests -v
npm run typecheck --prefix studio/web
npm test --prefix studio/web
npm exec --prefix studio/web -- playwright install chromium
npm run test:browser --prefix studio/web
npm run build --prefix studio/web
python3 tools/check_skills.py
python3 creation-lab/registry/verify_sources.py
```

The opt-in CPU Blender fixture uses `STUDIO_BPY_PYTHON=/absolute/existing/python` with the Python test command. Browser tests use software rendering for deterministic functional checks; they do not measure production GPU performance. Live provider and GPU execution have separate receipts. Existing library, bridge and creation tests remain part of CI.
