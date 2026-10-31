# micro:bit V2 interactive 3D model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an original, detailed micro:bit V2 GLB plus a Studio `microbit` factory so pressing A, B or the logo in the Studio preview lights the 25 LEDs, with lab-grade evidence.

**Architecture:** The Blender iterative flow (blockout → independent review → detail) produces a GLB whose parts are identified by `part_id` (the node contract). A trusted Studio factory wraps that GLB and exposes scalar channels `a`, `b`, `logo` (0..1) and `led.X.Y` (0..255, MakeCode's unit). Scenes drive LEDs with a code-free `patternBindings` array and ordinary timeline tracks; the preview gains pointer-hold picking and a scale-aware stage so a 5 cm object is usable.

**Tech Stack:** Python 3.10+ `unittest` (creation-lab, studio core), Blender 5.2.3 (native Windows exe via WSL), TypeScript 5.9 / three 0.180 / vitest 3.2 / Playwright 1.56 / Vite 7.

**Spec:** `docs/superpowers/specs/2026-10-30-microbit-v2-interactive-design.md` (approved; amended during planning: lowercase slug `part_id`s, no root node, `behavior: "microbit"` instance field).

## Global Constraints

- Work on branch `feat/microbit-v2-interactive`; commit messages end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Do not push or open a PR unless asked.
- Preserve `models/`, `index.json`, historical receipts (`creation-lab/docs/iterative-validation.json`) and existing tests; existing scenes/tests must keep passing unchanged.
- Studio, its dependencies and runs stay out of the public inventory; runs live in git-ignored `.local`. New run per result; never overwrite reviewed evidence.
- Verdict words for creation work: `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`. Technical, visual, content and provenance are separate verdicts. Open real images before any visual claim. Software-rendered browser tests are functional evidence only; GPU performance and live MakeCode simulator wiring are `NOT_RUN`.
- Units metres. Blender: Z up, front −Y. Studio/glTF: Y up, front +Z. Board lies flat, LED face +Y, edge connector toward +Z. No implicit rescale; only a scene instance `scale` scales.
- Budgets (never relaxed): triangles ≤ 30000, materials ≤ 45, mesh objects ≤ 150, GLB ≤ 3145728 bytes, Studio draw calls ≤ 200. Nominal board 0.052 × 0.042 m (confirm against the official hardware spec before freezing the brief).
- Channels: `a`, `b`, `logo` ∈ 0..1; `led.X.Y` (X column, Y row, origin top-left, 0..4) ∈ 0..255. Overlapping patterns combine by per-LED maximum.
- `claude` mode IDs: coordinator `claude-sonnet-5-5` or `claude-opus-5-5`; author `claude-sonnet-5-5`, `claude-opus-5-5` or `claude-haiku-5-5`; reviewer `claude-opus-5-5` or `claude-sonnet-5-5` in a fresh context. Efforts as today. Never alias a Sol/Luna name; record requested vs actual model/effort for every role; no invented agent IDs, usage or cost.
- Excluded from the model: BBC / micro:bit logos, FCC ID, silkscreen text. Reference photos are reference-only: never textures, never committed.
- Creation-lab generators: `build()` with no args, Principled materials, `part_id` on every mesh, no lights/cameras/3D text/IO/network.
- Studio verification commands (repo root): `npm test --prefix studio/web`, `npm run typecheck --prefix studio/web`, `python3 -m unittest discover -s studio/tests -v`, `python3 -m unittest discover -s creation-lab/tests -v`. If Playwright refuses this OS, use the platform override documented in `studio/docs/AUTHORING.md`.

## Review Focus

1. A and B held together, then one released: LEDs show the other's pattern, never a stuck or blank board (Task 2 test, Task 6 browser test).
2. Pointer leaves the canvas, loses capture, tab hidden, or window blurs while a part is held: channel returns to 0 and orbit is re-enabled (Task 6).
3. Scene swap or unmount while a part is held, repeated mount/unmount: no stale handlers, materials disposed once (Task 5, Task 6).
4. GLB with a renamed/missing/duplicated part, or LED materials merged by an exporter: clear load error naming the part, not a silently partial board (Task 5, Task 8 checker).
5. Scene `scale` ≠ 1 and true 5 cm scale: picking, labels, bounds, near plane and zoom limits still work (Task 4, Task 6).

## File Structure

| Path | Responsibility |
|---|---|
| `creation-lab/iterate.py`, `tests/test_iterate.py`, `docs/MODELS.md`, `docs/ITERATIVE-WORKFLOW.md`, `../AGENTS.md` | `claude` mode policy |
| `studio/web/src/runtime.ts` | channel types, scene validation, pattern bindings, ownership |
| `studio/web/src/stage.ts` (new) | scale-aware camera/shadow/fog/grid parameters |
| `studio/web/src/microbit.ts` (new) | factory: contract check, LED/button/logo behaviour, pick, parts |
| `studio/web/src/assets.ts` | export `base`, add `parseGLB` |
| `studio/web/src/preview.ts` | `behavior` dispatch, pointer hold, controls, part labels, stage use |
| `studio/examples/microbit/` | `node-contract.json`, later `microbit.glb`, `microbit.scene.json`, provenance |
| `studio/tests/fixtures/microbit-scene-cases.json` | scene validity cases shared by TS and Python |
| `studio/core.py`, `contracts/records.schema.json` | Python/schema mirror of scene rules |
| `creation-lab/components/shapes.py` (new) | pure-Python board shapes |
| `creation-lab/experiments/microbit-v2/` | brief, generators, `check_contract.py`, evidence index |

---

### Task 1: `claude` mode in `iterate.py`

**Files:**
- Modify: `creation-lab/iterate.py:21-24,125-135,463`, `creation-lab/tests/test_iterate.py`, `creation-lab/docs/MODELS.md`, `creation-lab/docs/ITERATIVE-WORKFLOW.md`, `AGENTS.md` (production-workflow paragraph, Spanish)

**Interfaces:**
- Produces: `MODES` gains `'claude'`; `CLAUDE_MODELS = {'coordinator': {...}, 'author': {...}, 'reviewer': {...}}`; `allowed('claude', role)` returns `(set[str], EFFORTS)`; `init --mode claude`.

- [ ] **Step 0:** `git switch -c feat/microbit-v2-interactive`; stage and commit the spec and this plan (`docs: micro:bit V2 design and plan`).
- [ ] **Step 1: Write failing tests** in `test_iterate.py` (same fixture style as the existing `actor`/`init_session` tests): `test_claude_mode_role_models` (coordinator sonnet/opus ok, haiku rejected; author haiku ok; reviewer haiku rejected), `test_claude_ids_rejected_in_sol_luna_modes` (`mixed`, `sol`, `luna` each reject `claude-sonnet-5-5`), `test_sol_luna_ids_rejected_in_claude_mode`, `test_aliases_rejected_in_claude_mode` (`sonnet`, `opus`), `test_init_session_claude_mode` (session mode `'claude'`, then an `author` actor `claude-haiku-5-5` is accepted by `session_actor`).
- [ ] **Step 2:** Run `python3 -m unittest discover -s creation-lab/tests -p test_iterate.py -v`; expect the five new tests FAIL, all others pass.
- [ ] **Step 3:** Implement: extend `MODES` and `allowed()` (branch before the Sol/Luna `require`), widen the `--mode` choices, keep default `mixed`. Aliases stay rejected by the exact-ID check.
- [ ] **Step 4:** Rerun; expect all PASS, including the pre-existing tests unmodified.
- [ ] **Step 5:** Document the mode: MODELS.md and ITERATIVE-WORKFLOW.md (mode table row, IDs, "no claim of superiority"), AGENTS.md paragraph (Sol/Luna default unchanged; `claude` mode available by explicit choice). Run `python3 -m unittest discover -s creation-lab/tests -v`.
- [ ] **Step 6: Commit** `feat(creation-lab): add claude authoring mode`.

---

### Task 2: Scene data model and runtime (TypeScript)

**Files:**
- Modify: `studio/web/src/runtime.ts`, `studio/web/tests/runtime.test.ts`
- Create: `studio/tests/fixtures/microbit-scene-cases.json`

**Interfaces:**
- Produces (in `runtime.ts`):
  - `type Led = \`led.${0|1|2|3|4}.${0|1|2|3|4}\``; `type Channel = 'pressed'|'angle'|'a'|'b'|'logo'|Led`
  - `const MOMENTARY: readonly Channel[] = ['pressed','a','b','logo']`
  - `function channelRange(c: Channel): [number, number]` (`pressed`/`a`/`b`/`logo` → [0,1]; `angle` → [-180,180]; `led.*` → [0,255])
  - `type Grid = number[][]` (5 rows y × 5 columns x); `interface PatternBinding { source: 'a'|'b'|'logo'; target: string; released: Grid; pressed: Grid }`
  - `Instance.behavior?: 'microbit'`; `SceneSpec.patternBindings?: PatternBinding[]`
  - `interface PartInfo { id: string; label: string; anchor: THREE.Vector3; channel?: Channel }`; `Asset.parts?: PartInfo[]`; `Asset.pick?(object: THREE.Object3D): Channel | undefined`
  - `Runtime.owner()` additionally returns `{kind:'pattern'; source: string}`

- [ ] **Step 0:** `npm ci --prefix studio/web` (approved install); confirm `npm test --prefix studio/web` is green before changes.
- [ ] **Step 1: Write failing tests** in `runtime.test.ts` using a stub `Asset` (empty `Group`, `channels` = `a,b,logo` + 25 `led.*`, recording `set`): 
  - `pattern binding lights LEDs only while source pressed`: `input(id,'a',1)` → `value(id,'led.2.2')===255`; `input(id,'a',0)` → `0`.
  - `overlapping patterns combine by per-LED maximum`: A=100 and B=200 at `led.0.0`; both held → 200; release B → 100.
  - `nonzero released grid is the authored rest pose and survives reset()`.
  - `interactive input cannot write a pattern-owned LED` (`input(id,'led.0.0',50)` ignored); `owner()` returns `{kind:'pattern',source:'a'}`.
  - `timeline track on an LED takes precedence in timeline mode; pattern resumes in interactive mode`.
  - `release() frees pressed, a, b and logo`.
  - `validateScene` rejects every `invalid` case and accepts every `valid` case in the fixture file. Fixture cases (full minimal scenes): valid microbit scene with pattern bindings and an LED track; invalid: `led.5.0`, `led.0.5`, `led.0.0` value 256, `a` value 2, `a` track on instance without `behavior`, `behavior: "microbit"` on a built-in asset, unknown `behavior`, grid with 4 rows, grid with 4 columns, grid value -1, non-finite value, pattern target not microbit, pattern source `pressed`, duplicate (source,target), extra keys on a pattern binding.
- [ ] **Step 2:** Run `npm test --prefix studio/web`; expect new tests FAIL.
- [ ] **Step 3:** Implement the types, `validateScene` rules (channel allowed per instance kind: `pressed`→button, `angle`→servo, `a|b|logo|led.*`→`behavior==='microbit'`; ranges via `channelRange`; patternBindings checked as the cases require, ≤ 100) and runtime evaluation in `applyBindings` (max over bindings of `lerp(released[y][x], pressed[y][x], value(source))`, skipped for LEDs a timeline owns). Generalise `input` clamping and `release()` to `MOMENTARY`. Existing button/servo behaviour unchanged.
- [ ] **Step 4:** `npm test --prefix studio/web && npm run typecheck --prefix studio/web`; expect all PASS (existing 23 tests included).
- [ ] **Step 5: Commit** `feat(studio): micro:bit channels and pattern bindings in the scene runtime`.

---

### Task 3: Python validator and JSON schema parity

**Files:**
- Modify: `studio/core.py:~175-220`, `studio/contracts/records.schema.json` (track `channel` enum, instance `behavior`, `patternBindings`), `studio/tests/test_core.py`

**Interfaces:**
- Consumes: the fixture file from Task 2.

- [ ] **Step 1: Failing test** `test_microbit_scene_cases_match_typescript` in `test_core.py`: loads `studio/tests/fixtures/microbit-scene-cases.json`; every `valid` case passes the scene validator (same entry point existing scene tests use), every `invalid` case raises `ValueError`. Add `test_schema_lists_microbit_channels` asserting the schema's channel enum contains `a`, `b`, `logo` and that `behavior` and `patternBindings` are declared.
- [ ] **Step 2:** `python3 -m unittest studio.tests.test_core -v` (or discover with `-p test_core.py`); expect FAIL.
- [ ] **Step 3:** Mirror the Task 2 rules in `core.py` (error messages free) and extend the schema; keep `studio.py` built-in allowlists untouched (a `behavior` instance uses a `.glb` path and goes through the existing inventory checks).
- [ ] **Step 4:** `python3 -m unittest discover -s studio/tests -v`; expect all PASS (72 existing + new).
- [ ] **Step 5: Commit** `feat(studio): validate micro:bit scenes in the Python core and schema`.

---

### Task 4: Scale-aware stage

**Files:**
- Create: `studio/web/src/stage.ts`, `studio/web/tests/browser/scale.spec.ts`
- Modify: `studio/web/src/preview.ts` (`frame()`, camera/controls/shadow/fog/grid/ground setup), `studio/web/tests/runtime.test.ts` (or a new `stage.test.ts`)

**Interfaces:**
- Produces: `interface Stage { near: number; minDistance: number; maxDistance: number; shadowExtent: number; fogNear: number; fogFar: number; gridSize: number; frameFloor: number }` and `function stageForBounds(longest: number): Stage`.

- [ ] **Step 1: Failing unit tests:** `stageForBounds(6)` equals exactly the current constants `{near:.05,minDistance:2,maxDistance:22,shadowExtent:8,fogNear:12,fogFar:35,gridSize:30,frameFloor:1.4}`; `stageForBounds(0.0525)` is each value × `0.0525/2` (`toBeCloseTo` relative 1e-9); `stageForBounds(0)`, `NaN`, negative → the default (same as 6). Scale factor `min(1, longest/2)`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement `stage.ts`; in `preview.ts` apply it from the scene's world bounds after each load and in `frame()` (camera near + `updateProjectionMatrix`, `controls.minDistance/maxDistance`, shadow camera extents, fog, grid/ground scale, the `1.4` distance floor). Workbench scenes must behave identically.
- [ ] **Step 4:** Browser test `scale.spec.ts`: a scene with the built-in button at instance scale `[0.02,0.02,0.02]` loads, Frame scene shows it unclipped (read `camera.near` and orbit distance from the capture receipt: `near < distance`, `distance` within `[minDistance, maxDistance]`); the default workbench receipt is unchanged in near/min/max. Run `npm run test:browser --prefix studio/web` (install Chromium first with `npm exec --prefix studio/web -- playwright install chromium`); expect PASS with the existing 11 browser tests.
- [ ] **Step 5: Commit** `feat(studio): scale-aware stage for centimetre-size objects`.

---

### Task 5: `microbit` factory and node contract

**Files:**
- Create: `studio/examples/microbit/node-contract.json`, `studio/web/src/microbit.ts`, `studio/web/tests/microbit.test.ts`, `studio/web/tests/fixtures/contract-board.ts`
- Modify: `studio/web/src/assets.ts` (export `base`; add `parseGLB`; `loadGLB` uses it, behaviour unchanged)

**Interfaces:**
- Produces: `node-contract.json` = `{schemaVersion:1, units:'m', parts:[{id,label}], pickable:{btn_a:'a',btn_b:'b',btn_a_cap:'a',btn_b_cap:'b',logo_touch:'logo'}, caps:{btn_a_cap:'a',btn_b_cap:'b'}, pressTravelMeters:0.0005, ledEmissive:{color:'#ff2a1a', maxIntensity:3}, ledGrid:{columns:5,rows:5,maxBrightness:255}}` listing every part_id from the spec's table.
- `parseGLB(url: string, signal: AbortSignal): Promise<{scene: THREE.Group; animations: THREE.AnimationClip[]}>` (same self-contained-GLB rules).
- `createMicrobit(source: THREE.Object3D): Asset` (28 channels: `a`,`b`,`logo`, 25 `led.X.Y`; `parts` with a top-surface anchor per part; `pick` resolving a hit object's ancestors to a momentary channel); `loadMicrobit(url: string, signal: AbortSignal): Promise<Asset>`.
- `makeContractBoard(): THREE.Group` (test fixture: one mesh per contract part, `userData.part_id`, unique material per LED).

- [ ] **Step 1: Failing tests** in `microbit.test.ts`:
  - `rejects a board missing led_3_4` (error message contains `led_3_4`); `rejects duplicate part_id`; `rejects LEDs sharing a material` (message contains `distinct material`).
  - `rest state: every LED emissiveIntensity is 0 and emissive color equals the contract color`.
  - `set('led.1.2',255) lights only that LED to maxIntensity; set(...,0) restores 0`; `set('led.1.2',128)` is half intensity (`toBeCloseTo`).
  - `set('a',1) moves btn_a_cap down by pressTravelMeters along local Y; set('a',0) restores the exact original position; btn_b_cap untouched`.
  - `pick maps btn_b_cap child → 'b', logo_touch → 'logo', pcb → undefined`.
  - `channels has 28 unique entries`; `dispose() releases geometry/materials once and a second dispose is a no-op`.
- [ ] **Step 2:** Run `npm test --prefix studio/web`; expect FAIL.
- [ ] **Step 3:** Implement. Resolve nodes by `userData.part_id` (the loader maps glTF extras there); set LED emissive colour/zero intensity at load; wrap with `base(...)` for scope/dispose; fail closed with part-naming errors.
- [ ] **Step 4:** `npm test --prefix studio/web && npm run typecheck --prefix studio/web`; expect PASS.
- [ ] **Step 5: Commit** `feat(studio): micro:bit factory against the node contract`.

---

### Task 6: Preview interaction

**Files:**
- Modify: `studio/web/src/preview.ts` (`load()`: `i.behavior==='microbit'` → `loadMicrobit(new URL(i.asset, baseURL).href, signal)`; `select()`; pointer handlers; labels), `studio/web/src/style.css` if needed
- Create: `studio/web/tests/browser/microbit.spec.ts`

**Interfaces:**
- Consumes: Task 2 `Asset.parts/pick`, `MOMENTARY`; Task 5 `loadMicrobit`; Task 4 stage.

- [ ] **Step 1: Failing browser tests** (serve a contract-conformant GLB built in-page with `GLTFExporter` from `makeContractBoard()` through `page.route`; scene with `behavior:"microbit"`, one `patternBindings` entry per source with distinct grids):
  - `inspector Hold A lights the A pattern; releasing clears it` (read the LED state from the inspector's "N LEDs lit" readout and from the capture receipt's `channels`).
  - `pointer hold on the A part` (take screen coordinates from the part's label element rect with Anchors off; `mouse.down` → pattern lit and orbit disabled; `mouse.up` → cleared, orbit enabled).
  - `A and B held, release A: B pattern remains`.
  - `pointercancel, blur and visibilitychange while holding release the channel`.
  - `scene swap while holding` and `mount/unmount ×3` produce zero console errors.
  - `scene scale 10× keeps picking and labels aligned`.
  - Existing 11 browser tests unchanged.
- [ ] **Step 2:** Run `npm run test:browser --prefix studio/web`; expect the new tests FAIL.
- [ ] **Step 3:** Implement: dispatch on `behavior`; for microbit `select()` shows three momentary controls (Hold A / Hold B / Hold logo, `bindHold`, keyboard Space/Enter) and a state readout; pointerdown raycast → `asset.pick(hit.object)` → `runtime.input(id, channel, 1)`, `setPointerCapture`, `controls.enabled=false`; release on pointerup, pointercancel, lostpointercapture, window blur, visibilitychange and unmount (reuse the existing teardown list); part labels from `asset.parts` shown with the Anchors toggle; selection by click unchanged. Reduced-motion rules unchanged.
- [ ] **Step 4:** `npm run typecheck --prefix studio/web && npm test --prefix studio/web && npm run test:browser --prefix studio/web && npm run build --prefix studio/web`; expect all PASS.
- [ ] **Step 5: Commit** `feat(studio): pointer-hold micro:bit interaction in the preview`.

---

### Task 7: Board shape components

**Files:**
- Create: `creation-lab/components/shapes.py`
- Modify: `creation-lab/components/__init__.py`, `creation-lab/components/README.md`, `creation-lab/tests/test_components.py`

**Interfaces:**
- Produces (pure Python, return `MeshData`, meshes pass `validate_mesh`):
  - `rounded_rect_outline(width: float, height: float, radius: float, segments: int = 6, center=(0, 0)) -> list[tuple[float, float]]` (counter-clockwise)
  - `circle_outline(radius: float, segments: int = 24, center=(0, 0)) -> list[tuple[float, float]]`
  - `extruded_outline(outline, holes=(), thickness: float = 0.001, z0: float = 0.0) -> MeshData` (ear clipping with hole bridging; holes inside the outline, non-overlapping)
  - `rounded_box(size: tuple[float, float, float], radius: float, center=(0, 0, 0), segments: int = 3) -> MeshData`
  - `cylinder(radius: float, height: float, center=(0, 0, 0), segments: int = 24) -> MeshData`

- [ ] **Step 1: Failing tests** in `test_components.py`: `extruded_outline` of a 0.052×0.042 rounded rect with five circular holes → `validate_mesh` ok, `boundary_edges == 0`, volume within 1% of (outline area − hole areas) × thickness; a hole crossing the outline or another hole raises `ValueError`; winding exterior (signed volume > 0); `rounded_box` volume within 2% of the analytic value and closed; `cylinder` triangle count `4*segments`; PCB at default segments under 3000 triangles.
- [ ] **Step 2:** Run `python3 -m unittest discover -s creation-lab/tests -p test_components.py -v`; expect FAIL.
- [ ] **Step 3:** Implement and export; document each function in the components README (contract, units, limits).
- [ ] **Step 4:** Run the same command plus, when Blender is available, `CREATION_TEST_BLENDER=<blender> …`; expect PASS.
- [ ] **Step 5: Commit** `feat(creation-lab): extruded and rounded board components`.

---

### Task 8: Brief, contract checker and blockout

**Files:**
- Create: `creation-lab/experiments/microbit-v2/brief.json`, `generator_blockout.py`, `check_contract.py`, `README.md`; `creation-lab/tests/test_microbit_contract.py`

**Interfaces:**
- `check_contract.py`: `read_glb_json(path: Path) -> dict`; `check_contract(gltf: dict, contract: dict) -> list[str]` (problems; empty = pass) verifying every contract `part_id` appears exactly once in node extras, the 25 LED nodes reference 25 distinct materials, and the GLB bounding box matches `displayScale`; CLI `python3 check_contract.py GLB` exits 1 on problems. Contract file: `studio/examples/microbit/node-contract.json`.
- `brief.json`: valid for `validate_brief`; `parts` = contract `part_id`s with labels; `displayScale {units:'m', longestDimension:0.052, tolerance:0.02}`; the four budgets from Global Constraints; `seed` int; provenance `{author:'GuateGeeks', origin:'Original model from the official hardware specification; photos used as reference only', license:'MIT'}`; `blockoutChecks` and `contentChecks` taken from the spec's Content gate (LED grid centred 5×5; A left and B right of it; logo above; pins 0,1,2,3V,GND left→right on the edge; USB, reset, battery socket, speaker, mic on the back).

- [ ] **Step 1: Failing tests** in `test_microbit_contract.py` using a synthetic minimal GLB written by the test (JSON chunk + empty BIN): conformant → `[]`; missing `led_3_4` → problem names it; duplicate `part_id`; two LEDs on one material → "distinct material"; box 20% too large → dimension problem; `brief.json` passes `iterate.validate_brief`.
- [ ] **Step 2:** Run `python3 -m unittest discover -s creation-lab/tests -p test_microbit_contract.py -v`; expect FAIL.
- [ ] **Step 3:** Implement checker and brief. Write `generator_blockout.py` (`build()` returns `title`, `design_notes`, `parts` → `{label_position}`) with every part as a simple volume from `components.shapes`, true size, centred.
- [ ] **Step 4:** Tests PASS; then run the flow from `ITERATIVE-WORKFLOW.md`: `iterate.py init --mode claude` (coordinator Sonnet 5.5 medium), `run --stage blockout` with the WSL Blender path, `review-template`. A **fresh-context reviewer** (Opus 5.5 medium) opens all six images, fills the template and `iterate.py review` records it; `iterate.py status` must show `READY_FOR_DETAIL`. If not, spend a correction (max two in total across stages), preserving failures and new evidence.
- [ ] **Step 5: Commit** `feat(creation-lab): micro:bit brief, contract checker and approved blockout` (evidence stays in `.local`; index run IDs and hashes in the experiment README).

---

### Task 9: Detail, installation into Studio, evidence and docs

**Files:**
- Create: `creation-lab/experiments/microbit-v2/generator_detail.py`, `studio/examples/microbit/microbit.glb`, `studio/examples/microbit/microbit.scene.json`, `studio/examples/microbit/PROVENANCE.md`, `studio/web/scripts/generate-microbit-scene.mjs`, copies under `studio/web/public/microbit/`, `studio/web/tests/browser/microbit-asset.spec.ts`
- Modify: `studio/docs/AUTHORING.md`, `studio/docs/STATUS.md`, `creation-lab/docs/STATUS.md`, `.agents/skills/gg3d-studio/SKILL.md`

- [ ] **Step 1:** Write `generator_detail.py` (all contract parts with real detail: gold edge fingers and five pin rings, scalloped PCB, tactile buttons with caps, 25 individually material'd LEDs, back-side components) and run `iterate.py run --stage detail`; reviewer pass as in Task 8. Corrections only from the remaining shared budget; a spent budget stays `BLOCKED` with pending defects, never a relaxed gate.
- [ ] **Step 2:** Technical gate on the approved run: budgets, reopen/reimport QA, `python3 creation-lab/experiments/microbit-v2/check_contract.py <run>/asset.glb` → exit 0; record hashes.
- [ ] **Step 3:** Install the approved GLB under `studio/examples/microbit/` and `studio/web/public/microbit/` with PROVENANCE (original work, MIT, reference photos not included). Generate `microbit.scene.json` (`behavior:"microbit"`, three distinct patterns for A/B/logo, an LED timeline track set replaying a short sequence) with the script. Add a unit test asserting the two GLB/scene copies are byte-identical.
- [ ] **Step 4: Browser test** `microbit-asset.spec.ts` against the real GLB: holding A, B, logo each yields a different non-empty LED set; release clears; 25 LED channels present; zero console errors. Run `python3 studio/studio.py project init microbit --scene studio/examples/microbit/microbit.scene.json --author GuateGeeks --license MIT` then `validate` on the project; capture PNGs with receipts in rest, A-held, B-held, logo-held states.
- [ ] **Step 5:** A fresh-context reviewer opens the capture PNGs and the six lab renders and dictates the separate visual and content verdicts; the coordinator records them with requested vs actual model/effort. `NOT_RUN` entries: GPU performance, live simulator.
- [ ] **Step 6:** Docs: AUTHORING.md (micro:bit channels, units, node contract, `behavior`, `patternBindings`, stage scaling, and the contract a future simulator feed must follow); both STATUS files link the evidence; gg3d-studio skill gets only the decision-changing lessons (scale-aware stage; `behavior` field; part_id contract). Run the full verification list: Studio Python and web unit/browser/typecheck/build, creation-lab tests, `python3 tools/check_skills.py`, `python3 creation-lab/registry/verify_sources.py`.
- [ ] **Step 7: Commit** `feat: interactive micro:bit V2 model and Studio demo`; report verdicts and remaining `NOT_RUN` items; do not push.

---

## Self-review

- Spec coverage: goals 1–5 → Tasks 8–9, 5, 2/6, 9, 9; node contract → 5, 8; channels/patterns → 2–3; input/rendering/camera → 4–6; flow, budgets, gates → 8–9; Claude-mode decision → 1; calls and non-goals honoured (no logos/text, no simulator wiring).
- Names checked across tasks: `Channel`, `MOMENTARY`, `PatternBinding`, `PartInfo`, `stageForBounds`, `createMicrobit`/`loadMicrobit`, `parseGLB`, `check_contract`, `makeContractBoard`.
- Proportion: the plan decides names, interfaces, values and tests and leaves bodies to the builder.
