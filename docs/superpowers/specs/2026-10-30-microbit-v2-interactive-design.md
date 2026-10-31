# micro:bit V2 interactive 3D model — design

Status: DRAFT for approval · 2026-10-30 · scope: `3d-assets` only (Studio preview)

## Intent and why

Students program the micro:bit in MakeCode and watch a flat 2D board in the
simulator. We want a detailed 3D micro:bit V2 that they can orbit, and whose
A button, B button and gold touch logo can be pressed with the pointer, with
the 25 LEDs reacting. The lab must prove the asset and its behaviour first;
Code Studio / the MakeCode editor are later consumers (AGENTS.md: "el trabajo
actual se completa y valida aquí primero").

The behaviour is proven in the **Studio preview** only. The LEDs react to
declarative, code-free "show this pattern while pressed" bindings plus a
recorded LED timeline. A live feed from the MakeCode simulator is a later cut;
this cut defines and tests the channel contract that feed will use.

## Goals

1. A detailed, original GLB of the board at true size (nominal 52 × 42 mm;
   the builder confirms against the official hardware spec before freezing
   the brief — photos give proportion only), front and back faces, produced
   by the Blender iterative flow with preserved evidence.
2. A fixed **node contract** (below) so Studio can drive and pick parts.
3. A trusted Studio `microbit` factory: channels, pointer/keyboard input,
   LED emissive rendering, button/logo press feedback, part labels.
4. A scene + brief + tests showing A, B and logo each produce a distinct,
   visible LED pattern, and a recorded LED timeline replays.
5. Technical, visual, content and provenance gates dictated separately.

## Non-goals

- Live wiring to the MakeCode simulator, the editor, Code Studio, or Sócrates.
- Electrical/physics simulation; accelerometer, compass, speaker, microphone,
  radio or pin-level behaviour (parts are modelled, not driven).
- BBC / micro:bit logos, FCC ID and silkscreen text. (My call, see below.)
- A generic "bind any GLB node" grammar in scene JSON (rejected approach B).
- Catalog promotion, `index.json` entries, rigging, Meshy generation.

## Anti-goals (failure even if it "works")

- LEDs that merely look lit through a static texture, or shared materials
  so that one LED lights several.
- One fused mesh, or buttons/LEDs that cannot be picked or moved.
- Passing only the Studio fake patterns while the GLB is visually weak.
- Relaxing a budget or tolerance, or citing a process exit as quality.
- Presenting the recorded feed or pattern bindings as simulator validation.

## Constraints

- AGENTS.md of this repo applies: preserve `models/`; new run per result;
  keep Studio, its deps and runs out of the public inventory; PASS / FAIL /
  BLOCKED / NOT_RUN for creation; open real images before any visual claim;
  one heavy GPU load (this work is CPU-only); two correction rounds total on
  top of the first blockout and first detail.
- Units metres, explicit axes. Blender: Z up, front −Y. Studio/glTF: Y up,
  front +Z. Board lies flat, LED face toward +Y, edge connector toward +Z.
  No implicit rescale; instance `scale` in the scene is the only scaler.
- GLB self-contained (no external buffers/textures), per Studio's loader.
- Generators follow the creation-lab contract: `build()`, Principled
  materials, `part_id` on every mesh, no lights/cameras/3D text/IO.
- Reference photos (BBC / Micro:bit Educational Foundation imagery) are
  references only: not textures, not redistributed in the repo.
- Reproducible from the repo; no host path copied from a historical receipt.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| A | Everything in Studio code from primitives | One place, but blocky; skips lab evidence pipeline |
| B | Blender GLB + generic node-binding grammar in scene JSON | Reusable, but a new security-sensitive grammar before any micro:bit exists |
| **C** | **Blender GLB + trusted `microbit` factory (chosen)** | Lab quality gates plus small behaviour code; two parts must stay in sync (node contract + tests) |

Chosen by the user: **C**. Meshy image-to-3D was dropped (credits, fused mesh,
no separable parts, rights).

## Design

### 1. Node contract (GLB ⇄ Studio)

Names are exact; the factory fails closed with a clear error if any is missing
or duplicated. They are the `part_id` values (glTF `extras`), and lowercase
because the lab's brief validator accepts only slug IDs (amended 2026-10-30
while planning; this also drops the empty root node, since every part must be a
mesh and Studio wraps the GLB in its own root). The origin is the board centre
on the PCB mid-plane.

| part_id | Purpose |
|---|---|
| `pcb`, `edge_connector` | substrate and gold fingers |
| `pin_0`, `pin_1`, `pin_2`, `pin_3v`, `pin_gnd` | five large pin rings (labelled) |
| `btn_a`, `btn_b`, `btn_a_cap`, `btn_b_cap` | tactile buttons; each `_cap` translates when pressed; pickable |
| `logo_touch` | gold touch pad; pickable; press feedback |
| `led_x_y`, x,y ∈ 0..4 | 25 LEDs, **x = column, y = row, origin top-left**, matching MakeCode `led.plot(x, y)`. Each has its own uniquely named material `led_x_y` |
| `usb`, `reset_btn`, `battery_socket`, `speaker`, `mic`, `mic_led`, `processor`, `antenna`, `accel_compass` | modelled, labelled, not driven |

The factory resolves nodes by `part_id`, never by Blender object name. Materials
are not merged on export; the technical gate asserts 25 distinct LED materials
survive GLB roundtrip, and the factory itself sets emissive colour and zero
intensity at load, so the rest state does not depend on exporter behaviour.

### 2. Studio factory and runtime

- New trusted factory `microbit` (source in `studio/web/src`), wrapping the GLB
  via the existing self-contained loader. A scene instance selects it with an
  optional enum field `behavior: "microbit"` next to its relative `.glb` path
  (amended while planning: scene validators need to know which instances own the
  micro:bit channels without reading the GLB). The enum picks among compiled
  factories like `button` does; JSON still cannot supply code.
- Channels (scalar, same value map as today): `a`, `b`, `logo` in 0..1;
  `led.X.Y` in **0..255** — the simulator's own brightness unit — so a later
  feed maps 1:1. The `Channel` type, `validateScene` and `Runtime.reset/release`
  are generalised minimally; button/servo behaviour and existing tests must not
  change.
- Declarative `pattern` binding (restricted like today's button→servo binding,
  no code, no cycles): `source` ∈ {a, b, logo}, `released` and `pressed` 5×5
  grids of 0..255. Overlapping active patterns combine by per-LED maximum
  (my call). Interactive input cannot write a bound LED; timeline mode may
  own LED tracks, with the same ownership rules as `angle`.
- Input: pointer hold on `BTN_A`/`BTN_B`/`LOGO_TOUCH` sets the channel to 1 and
  releases on pointer-up/cancel/lost-capture/blur/teardown (reuse `bindHold`
  semantics). Inspector gets A/B/logo momentary controls so keyboard
  (Space/Enter) and screen readers work. Reduced-motion rules unchanged.
- Rendering: LED brightness drives that LED material's emissive intensity;
  buttons depress by a real-scale offset; logo shows touched state.
- Camera: a 5 cm object breaks defaults (near plane, min zoom distance). The
  builder verifies orbit, zoom, picking and bounds at true scale rather than
  scaling the GLB.

### 3. Demo scene and recorded feed

`studio/examples/microbit.scene.json`: one board, interactive mode, three
distinct patterns (A, B, logo — e.g. heart, smile, check; builder picks) and a
timeline track set that replays a short LED sequence. Both documented as
stand-ins for the future simulator feed; the contract (units, names, 0..255)
is written in `studio/docs/AUTHORING.md`.

### 4. Production flow (creation-lab)

0. First, the `claude` mode policy change (decision section), tested alone.
1. Brief `creation-lab/experiments/microbit-v2/brief.json`: purpose, `parts`
   (the node contract), `displayScale` (true size + tolerance),
   `blockoutChecks` vs `contentChecks`, budgets, provenance.
2. New reusable components in `creation-lab/components` (existing ones are
   closed ellipsoids): outlined/extruded plate with notches and holes (PCB with
   edge scallops and pin holes), rounded box, ring — each with tests.
3. Blockout run → six images → independent review → detail run → review. At
   most two corrections in total. New run per result; hashes recorded.
4. Export GLB, reopen `.blend`, reimport GLB, QA with
   `lab/scripts/creation_geometry.py`; copy the approved GLB into
   `studio/examples/microbit/` with PROVENANCE and licence (original work,
   MIT, consistent with the other Studio examples).

### 5. Budgets (my call; the brief fixes them and they are not relaxed)

triangles ≤ 30 000 · materials ≤ 45 · mesh objects ≤ 150 · GLB ≤ 3 MB ·
Studio draw calls within its existing 200.

### 6. Verification and evidence

- Technical: budgets; node-contract check; 25 distinct materials; dimensions
  within tolerance on all axes; build/reopen/reimport; Studio python +
  vitest + Chromium tests incl. press→pattern, release on blur/cancel,
  timeline ownership, repeated mount/unmount, disposal.
- Visual: six renders + Studio PNG capture and receipt **opened** by an
  independent context; judged for legibility of LED grid, A/B/logo, pins.
- Content: required parts present, in the right places (LED grid centred;
  A left, B right of it; logo above; pins 0,1,2,3V,GND left→right at the edge;
  USB, reset button, battery socket, speaker, mic on the back).
- Provenance: author, licence, reference-only photos, no BBC/micro:bit marks.
- Software-rendered browser tests are functional evidence, not GPU performance.

### 7. Environment

Native Windows Blender is the verified host (`…/Blender/blender.exe`, reached
from WSL by the existing wrapper pattern in
`creation-lab/benchmarks/claude-animal-cell/wsl-blender.sh`). Studio needs
`npm ci --prefix studio/web` (not yet installed here) and a Chromium install
for browser tests. No installs happen before this design is approved.

## Calls I made (flag any you disagree with)

1. Omit BBC / micro:bit logos, FCC ID and silkscreen text; Studio labels name
   parts instead. Also keeps trademarks out and fits the "no 3D text" rule.
2. LED brightness 0..255 and `led_x_y` naming copy MakeCode's contract.
3. Pattern overlap = per-LED max; three patterns chosen by the builder.
4. Orientation: LED face +Y, edge connector toward +Z.
5. Budgets in §5.
6. Studio-side behaviour is limited to the code-free pattern binding and
   timeline tracks.
7. The Claude-ID policy is a new `claude` mode with the per-role IDs listed
   in the decision section, rather than loosening the existing three modes.

## Decision: Claude IDs in production sessions (user's choice)

`creation-lab/iterate.py` accepts only `gpt-6.1-sol` / `gpt-6-luna` outside
`benchmark` mode. This session runs on Claude, so the user chose to **allow
Claude IDs in production mode**. This is a lab policy change and is the first
work item of the plan, done before any micro:bit geometry:

- **Interpretation (correct me on review):** add a fourth non-benchmark mode,
  `claude`, beside `sol` / `mixed` / `luna`. The existing three keep their exact
  semantics, so their tests and historical receipts stay valid. Claude IDs are
  still rejected in the three Sol/Luna modes, and no ID is ever aliased or
  renamed; a false Sol/Luna name stays forbidden.
- **Allowed IDs per role in `claude` mode (my call):** coordinator
  `claude-sonnet-5-5` or `claude-opus-5-5`; author `claude-sonnet-5-5`,
  `claude-opus-5-5` or `claude-haiku-5-5` (bounded components); reviewer
  `claude-opus-5-5` or `claude-sonnet-5-5`, always a fresh, separate context
  with the images opened. Default effort `medium`, `high` only for hard
  diagnosis, as today.
- **Same-commit updates:** `iterate.py`, its tests (new cases for `claude` mode
  and for cross-family rejection), `creation-lab/docs/MODELS.md`,
  `ITERATIVE-WORKFLOW.md`, and the production-workflow paragraph in AGENTS.md.
  A new validation receipt is recorded; the old `iterative-validation.json`
  stays a historical record and is not rewritten.
- **Not implied:** that Claude-authored output is better or worse than
  Sol/Luna. Requested vs actual model/effort are recorded for every role; if
  the runtime cannot confirm one, that is recorded as unconfirmed.
- Remaining default behaviour (two correction rounds, independent review,
  separate gates) is unchanged.

## Left to the builder

Exact geometry and proportions from the references and spec; component API
names; the three demo patterns; TypeScript shape of the generalised channels;
inspector layout; camera clipping fixes; test layout.
