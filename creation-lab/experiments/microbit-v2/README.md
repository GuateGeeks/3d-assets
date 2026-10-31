# micro:bit V2 interactive model

Original 3D model of the BBC micro:bit V2 board at true size, produced with the
lab's iterative Blender flow in `claude` mode. Studio drives it through the node
contract in `studio/examples/microbit/node-contract.json` (A, B, touch logo and
25 individually lit LEDs, resolved by `part_id`). Spec:
`docs/superpowers/specs/2026-10-30-microbit-v2-interactive-design.md`.

Provenance: original geometry from the official hardware specification
(https://tech.microbit.org/hardware/, outline from the V2.2 revision page: 51.60 x
42.00 x 11.65 mm). Photos were used as proportion references only: never textures,
never copied here. No BBC or micro:bit logos, FCC ID or silkscreen text. MIT.
The official V2.2 outline is 51.60 x 42.00 x 11.65 mm
(https://tech.microbit.org/hardware/2-2-revision/); the model is built at that
size, and the brief's `displayScale` 0.052 m (+/- 2 %) is a nominal value that
contains it (0.77 % off). PCB thickness (1.6 mm, consistent with the published
4.55 + 1.6 + 5.50 mm depths) and all component positions and sizes are estimated
from reference photos, not measured.

## Files

| File | Purpose |
| --- | --- |
| `brief.json` | Lab brief: parts = the node contract, `displayScale` 0.052 m +/- 2 %, budgets, blockout and content checks |
| `generator_blockout.py` | Blockout generator (`build()`), simple volumes at true positions, plates with clean Delaunay caps. It keeps its own frozen local `plate()` because the run snapshots that produced reviewed evidence contain it; the reusable version is `refined_plate` in `creation-lab/components/shapes.py`, used by the detail generator |
| `generator_detail.py` | Detail generator (`build()`): one object per contract part (pieces joined, flat hierarchy, identity transforms), single-material LEDs and touch logo, PCB caps from `components.refined_plate` |
| `render_extra_views.py` | HISTORICAL. Supplementary renders of run 001 only (the section below). Superseded by the official per-run `--extra-view underside` / `--extra-view top-down` of `iterate.py run`; kept as evidence of how run 001's supplementary images were made. Not part of the flow |
| `check_contract.py` | Stdlib GLB checker: each `part_id` once and on a mesh node, each LED a single-primitive mesh on a material no other node uses, press caps and their ancestors unrotated and unscaled, size within `displayScale` |
| `../../tests/test_microbit_contract.py` | Tests for the checker and the brief (synthetic GLBs, no Blender) |

Blender conventions: metres, Z up, front -Y. The board lies flat, LED face +Z
(+Y in glTF), edge connector toward -Y (+Z in glTF), origin at the board centre
on the PCB mid-plane. LED `led_x_y`: x column, y row, origin top-left seen from the
LED face with the edge connector at the bottom.

## Running

From the repository root (WSL with the native Windows Blender, adapter from the
Claude animal-cell benchmark; the adapter must be executable on the host, `chmod +x` it locally, the repo file mode is left alone):

```sh
export GG3D_WINDOWS_BLENDER=/path/to/blender.exe
python3 creation-lab/create.py doctor --blender $PWD/creation-lab/benchmarks/claude-animal-cell/wsl-blender.sh
python3 creation-lab/iterate.py init --brief creation-lab/experiments/microbit-v2/brief.json --mode claude --actor-id COORDINATOR_ID --model claude-sonnet-5-5 --effort medium
python3 creation-lab/iterate.py run --session SESSION --generator creation-lab/experiments/microbit-v2/generator_blockout.py --stage blockout --blender $PWD/creation-lab/benchmarks/claude-animal-cell/wsl-blender.sh --actor-id AUTHOR_ID --model claude-sonnet-5-5 --effort medium
python3 creation-lab/iterate.py run --session SESSION --generator creation-lab/experiments/microbit-v2/generator_blockout.py --stage blockout --blender $PWD/creation-lab/benchmarks/claude-animal-cell/wsl-blender.sh --actor-id AUTHOR_ID --model claude-sonnet-5-5 --effort medium --extra-view underside --extra-view top-down
python3 creation-lab/iterate.py run --session SESSION --generator creation-lab/experiments/microbit-v2/generator_detail.py --stage detail --blender $PWD/creation-lab/benchmarks/claude-animal-cell/wsl-blender.sh --actor-id AUTHOR_ID --model claude-opus-5-5 --effort medium --extra-view underside --extra-view top-down
python3 creation-lab/iterate.py review-template --session SESSION --run RUN_ID --output NEW_TEMPLATE.json
python3 creation-lab/experiments/microbit-v2/check_contract.py SESSION/runs/RUN_ID/asset.glb
```

The first blockout command is the run 001 form (six common views only); the second, with
`--extra-view`, is the form used for correction run 002, and the detail command above
also passes the two extra views. An independent reviewer context opens the six images (eight with the extra views) and fills the template;
`iterate.py review` records it. Tests: `python3 -m unittest discover -s creation-lab/tests -p test_microbit_contract.py -v`.

## Runs

Sessions and runs live in git-ignored `creation-lab/.local/`; this table indexes them.
Verdicts use PASS, FAIL, BLOCKED, NOT_RUN. Technical, visual and content are separate.

Session `creation-lab/.local/iterations/20261031T054439Z-105b17e2` (mode `claude`;
coordinator `claude-sonnet-5-5` medium, id `512a9441-9706-4b43-af04-b90df11ad0bc`; models requested, not confirmed by the runtime). Blender 5.2.3 LTS.

| Run ID | Stage | Author (requested) | Technical | Visual | Content | `asset.glb` sha256 |
| --- | --- | --- | --- | --- | --- | --- |
| `001-0c91b4d0cb9e` | blockout | `aff01f0d2db1ac83d`, `claude-sonnet-5-5` medium | PASS (46 meshes, 14400 triangles, 41 materials, 51.6 x 42.8 x 11.65 mm; `check_contract.py` PASS) | BLOCKED (recorded review: the six common views never show the underside) | BLOCKED (same reason; all six blockout checks PASS using the supplementary views) | `e134696aa431b3db921574c5c3206311f8c94f40edd7f41d9fac4a3ff28deaa9` |

Run `001-0c91b4d0cb9e` image hashes (sha256):

| Image | sha256 |
| --- | --- |
| `renders/front.png` | `bcdbae25e952d82ffeb7c9fb3dc3da64843bdeffa4ed30ec0df6bc2fe61e7e98` |
| `renders/side.png` | `1fd2ca8bfeb81a4128088c258a3e8615064838dd5dd76049312c9d84dfb03917` |
| `renders/back.png` | `885ee1176676f950cf3110d65b4241f95c41c89277c592e97369196d40ee01b9` |
| `renders/three-quarter.png` | `783b47c47f60ac2431270b5c15a20e6b39be6ff5480919866a918646808e3527` |
| `renders/wireframe.png` | `4164ede89e022e08cd18e9b505241a447ab53ff2846c413d80aef92ff674f469` |
| `renders/reimport-three-quarter.png` | `3b168f3be7b313ca3ff611b9dfac1adb81bb3b2a509c5ecee15501fce4af0747` |

`source.blend` sha256 `390e5a5f95a7f3d106ba4f980638a04fdfa7a95815129cd1dbd182e6a3d6ea75`.
The common six-view renderer uses fixed low or 3/4-from-above cameras, so the
back-face parts (USB, reset, battery socket, speaker, microphone, chips, antenna)
sit below the PCB and are not visible in those six images. Supplementary views
cover them without changing the worker or the run.

### Correction run 1 (blockout)

Same session, new run; spends correction 1 of 2. Reviewer verdict for run 001 was
visual BLOCKED and content BLOCKED (the six common views never show the underside).
Run 002 requests the official extra views `--extra-view underside --extra-view top-down`
(see `docs/ITERATIVE-WORKFLOW.md`, extra views). Generator `generator_blockout.py`
edited in place (git keeps run 001's version).

| Run ID | Stage | Author (requested) | Technical | Visual | Content | `asset.glb` sha256 |
| --- | --- | --- | --- | --- | --- | --- |
| `002-47a9ec5ebe91` | blockout, correction 1 | `aff01f0d2db1ac83d`, `claude-sonnet-5-5` medium | PASS (46 meshes, 16116 triangles, 41 materials, 51.6 x 42.8 x 11.65 mm; reopen PASS, reimport PASS; `check_contract.py` PASS) | PASS (recorded review) | PASS (recorded review) | `b9639f821566ea846393df715c57d066762d05cb434b37cc5355d4dde73bc2ca` |

`source.blend` sha256 `3b6c0dcdc5bf19d9f5cec4348099cb18f26dce2e23d0d63e4587a733512b13cd`.

Recorded reviews (`creation-lab/.local/iterations/20261031T054439Z-105b17e2/reviews/<run id>.json`):
both by a fresh-context reviewer with actor id `unknown-subagent-fresh-context`,
model `claude-opus-5-5`, effort `medium` as requested; the runtime did not confirm
the model or effort. Run 001: visual BLOCKED, content BLOCKED. Run 002: visual PASS,
content PASS, all eight images listed as opened (the six common views plus
`underside` and `top-down`); session status READY_FOR_DETAIL, corrections used 1 of 2.
The run 002 review lists these minor defects for the detail stage (none breaks a blockout check):
`mic_led` reads as a 26th LED (red square above LED column 4; make it smaller and
round or a different colour); back-face gold ring pads and finger strip missing
(add them to the existing `pin_*` / `edge_connector` parts); reset button about
4.4 mm against about 6 mm in photo 3.webp; antenna about 7 x 9 mm against about
10 x 13 mm in the photo (keep it a thin trace).

Image hashes (sha256), under `creation-lab/.local/iterations/20261031T054439Z-105b17e2/runs/002-47a9ec5ebe91/renders/`:

| Image | sha256 |
| --- | --- |
| `front.png` | `e1e0b2a5632e7fa305975b8b487649a4757b4a556c023bd30865711968bb447c` |
| `side.png` | `7615703056fbcbcfdfd1afd1323c98b39dc9841cf66cfdaaf3ea9bb864428f9b` |
| `back.png` | `e6c529ca002ef52278598095380d8e8b5481ce2fabffa9917a5cc16ab67e236a` |
| `three-quarter.png` | `e7e1e07d93e261680194b84fa901d108bb44495a0f7ddb55b083a2ec933d533a` |
| `wireframe.png` | `985eac74a3ffb0a496f455eb7b3849d822e14a004f3e4ee2652bff3b594e2c9c` |
| `reimport-three-quarter.png` | `bb8c472d638fa4242cc681f0f3633dafe0fb5fc9d76f8754a9cd9141acad3eab` |
| `underside.png` (extra view) | `727c427bce9afa29e7692ee62eb706a221fe7ec1ea82faf5f3a321b07dd80b35` |
| `top-down.png` (extra view) | `ae4f2b985e6eb3ac96066c9e132135c19865042e06d7ca14fe414723b0637340` |

Changes from run 001 (reviewer defects): speaker enlarged to a 10 mm diamond and
processor reduced to 5.5 mm; antenna is now a thin zigzag trace (0.7 mm wide)
instead of an 8 x 9 mm pad; reset body 4.5 mm; distinct blockout tones for the
back components; `mic_led` 1.3 mm and red; PCB caps re-triangulated (constrained
Delaunay with a 2.6 mm hex Steiner grid, subdivided outline; smallest cap angle
7.6 degrees instead of 0.007). The stray wire lines outside the board in run 001's
wireframe were the WIREFRAME modifier's even-offset spikes on those sliver
triangles, not stray geometry; the sliver fan was real and is fixed.

`deferred` (detail stage): gold fingers and ring pads on the back face of the edge
connector and pin parts (reviewer defect 3); front/side/back low-elevation views are
a renderer matter, covered by the extra views.

### Supplementary views (supplementary, not part of the common six-view renderer)

`render_extra_views.py` (sha256 `c2fac1322f7742c7e703c65db0bda811d4cd437d541dd088c36bbe61e34bd653`
is the version in commit `c10a15c` that rendered run 001's images; its docstring was
later marked HISTORICAL and its code is unchanged, so the file's current hash differs)
opens the run's saved `source.blend` read-only and renders with the worker's
settings (Cycles CPU, 2 threads, 24 samples, 768 px, AgX, same lights and world).
Output goes to a new folder `<session>/supplementary/<run id>/`; nothing in the
run folder is touched. Run through the same adapter, with the supplementary root
existing beforehand:

```sh
mkdir -p SESSION/supplementary
$PWD/creation-lab/benchmarks/claude-animal-cell/wsl-blender.sh --background --factory-startup --disable-autoexec --python-exit-code 1 --python $PWD/creation-lab/experiments/microbit-v2/render_extra_views.py -- SESSION/runs/RUN_ID SESSION/supplementary
```

Historical (run 001, superseded by the official extra views in run 002), folder `creation-lab/.local/iterations/20261031T054439Z-105b17e2/supplementary/001-0c91b4d0cb9e/`
(source.blend sha256 unchanged, `390e5a5f...`):

| Image | View | sha256 |
| --- | --- | --- |
| `back-face.png` | below, looking up, edge connector at the bottom (board mirrored left-right) | `95a75089c6214b6d720e83ec524740a17129737648b29f393fcf85f3c1e4a56b` |
| `top-down.png` | LED face straight on, edge connector at the bottom | `10495a4e07ebcc7afc3d06503385b420412fb8e9cc5fce95b08ad60f562b1713` |
| `back-three-quarter.png` | below, from the edge-connector side | `9c05a1c28fd607ab54408745cdb1fd75906c65238b07b271fd85f470c8f22491` |
| `back-three-quarter-rear.png` | below, from the USB / battery side | `591a33396f5027d95956132c356e3af00b556c458231aa5b2f0ee3a133b5ef51` |
| `supplementary.json` | manifest (renderer settings, image hashes) | `fb1f1f67dd849dbe59074ae269df30553cb67ebb40ecf0c84bea91a0b3ab3360` |

### Detail run (first detail, no correction spent)

Same session, after READY_FOR_DETAIL. Generator `generator_detail.py` (sha256
`fc6d780c0c9a6e81fb3f385eae691d5873512ae9f9946f106c4526be46df26e8`); the
components snapshot in the run's `code/` includes the new `refined_plate`.

| Run ID | Stage | Author (requested) | Technical | Visual | Content | `asset.glb` sha256 |
| --- | --- | --- | --- | --- | --- | --- |
| `003-9621bf5caaca` | detail | `af51c59431c74119a`, `claude-opus-5-5` medium (not confirmed by the runtime) | PASS (46 meshes, 22560 triangles, 43 materials, 51.6 x 43.25 x 11.65 mm, GLB 1117164 bytes; reopen PASS, reimport PASS; `check_contract.py` PASS) | PASS (recorded review) | PASS (recorded review) | `b12143d94deda3faaae36c154bc2177a5c9f1c6deccb102947d5e27a7fe13687` |

`source.blend` sha256 `ae02eacd2d1f90fa4371dddb3bc084af21c268cb9689e8a409bbfa75a24bf328`.
Review template (as generated, before the reviewer filled its copy): `creation-lab/.local/iterations/20261031T054439Z-105b17e2/review-detail-001.json`
(sha256 `be2cc8411c2d47f6af97c037c3d6ec263b613a9943425ec8367be5fd8e3b97b0`).

**Recorded review of run 003.** File `creation-lab/.local/iterations/20261031T054439Z-105b17e2/reviews/003-9621bf5caaca.json`
(git-ignored, not copied; sha256 `1e6aa5c99a0d552fe6ea821fd0ff908285a13c6386abe3723325de2357fb138d`).
Visual PASS, content PASS; all six brief checks PASS; the eight images were opened
(six common views plus `underside` and `top-down`) together with the reference photos
and enlarged crops. Reviewer: fresh context, actor id `unknown-subagent-fresh-context`,
model `claude-opus-5-5`, effort `medium` as requested; the runtime did not confirm the
model or effort that was served (so "requested, unconfirmed"). Session status after the
review: **PASS, next `handoff`, corrections used 1 of 2.**

Provenance verdict (separate from technical, visual and content): **PASS**. Author
GuateGeeks; original geometry from the official hardware specification (outline,
`tech.microbit.org`) with the reference photos used for proportions only (never
textures, not included in this repository); MIT licence; no BBC or micro:bit logo, no
FCC ID and no silkscreen text; every component position and size is an estimate and is
flagged as such under "Estimates" below. Details in `studio/examples/microbit/PROVENANCE.md`.

Non-blocking defects listed by the reviewer (no correction was spent on them):

1. The edge connector has 14 gold fingers (3/4/4/3 between the pads); the real board
   has about 20 narrower ones, and none sit outside pins 0 and GND.
2. On the underside, a small dark component between the reset button and the battery
   socket touches the reset housing and the JST socket wall (about 0.3 mm of clearance
   was requested; a possible solid intersection).
3. The gold ring around each pin hole is about 0.6 mm wide, against about 1 mm on the
   real board.

Limits stated by the reviewer: the speaker, microphone, processor, antenna and
accelerometer/compass are visible only in `underside.png` (the standard views show the
speaker as a sliver); per-LED materials, `part_id` uniqueness and the LED index
mapping are data-contract properties that renders cannot show, so those rest on the
technical gate (`check_contract.py` and the Studio factory), not on the renders.

**Final state of the session.** Status PASS, next `handoff`; corrections used 1 of 2.
The last correction was deliberately not spent (a coordinator decision): the three
defects above are non-blocking, so no further Blender run was made. The Studio-side changes made
afterwards (LED rest/lit look, authored scene camera) did not touch the GLB, which is
unchanged and still has the sha256 above. The Studio product captures were reviewed
separately and FAILED twice before passing; see `studio/docs/STATUS.md` and
`studio/web/evidence/microbit-visual-reviews/README.md`.

Image hashes (sha256), under `creation-lab/.local/iterations/20261031T054439Z-105b17e2/runs/003-9621bf5caaca/renders/`:

| Image | sha256 |
| --- | --- |
| `front.png` | `420226df6644aa87fe266a69eba562bf1d6bc803c55806414da29c71514a7da9` |
| `side.png` | `6c47f37751a573b9cda26c6e9447d53e56edc58b11a6df7c9f134b0da9edd30c` |
| `back.png` | `6e496980554028e785d9cde2f3a261939a8260f3a897ea8a2eb88eb1caa1dd76` |
| `three-quarter.png` | `7605aa9fdd07657c9a612980384bf6ae34e1644ed9135b5801d0ca466b04c96b` |
| `wireframe.png` | `951edb92684efa07612fb6ea896a3cc8a260d3ef17f238c8636d6289eff0410c` |
| `reimport-three-quarter.png` | `875ff49909a8d2244a25a6fabc13a5fe441291e04bd8301984f6d7495c9539a7` |
| `underside.png` (extra view) | `d531bafd5384c43e90a9896a6061d72296677b5dfe30710df0c3865a8742697a` |
| `top-down.png` (extra view) | `851534a482076b12c76e044e8310376e90712727585a364f32a4906dfb7e0d33` |

Run 002 review defects addressed: `mic_led` is a 0.9 mm round amber dome (not LED
red) at the indicator position of the photos; gold tombstone pads and fingers are
on both faces (back pieces joined into each `pin_*` and `edge_connector`, with a
plated barrel through each hole); reset is a 6.0 x 5.8 mm switch; the antenna is
a 0.55 mm meander trace about 11 x 12.5 mm on a 45-degree axis, as in the photo.

Decisions (detail):

- Every contract part is one object; extra pieces are joined, so non-LED parts
  can be multi-material (multi-primitive in glTF). LEDs and `logo_touch` stay
  single-material because the Studio factory requires a single material on them.
  Unlabelled components (USB interface chip, crystal, three SOT-23 regulators,
  two status LEDs, 60 passives, USB through-hole pads, front microphone port) are
  joined into `pcb`, so labels of the named parts stay on their own bounds.
- Palette: the blockout's 16 non-LED materials, retuned toward the photos (black
  plungers, steel switch covers, dark chips, grey speaker), plus 2 new ones
  (`mat_black_plastic`, `mat_passive`) and the 25 private LED materials (warm
  white packages, distinct values): 43 of 45.
- The touch logo is 0.3 mm proud (real copper is flush) so the 0.2 mm Studio
  logo press (`pressTravelMeters` x 0.4) does not sink it below the board.
- Geometry with coplanar same-facing overlaps renders dark Cycles specks (seen on
  the antenna stub in a scratch smoke test); the stub now starts at the
  meander's edge.

Estimates (from the reference photos at 16.2 px/mm and 8.0 px/mm, not measured
on a board; tech.microbit.org gives only the outline and the three depths): LED
pitch 4.0 x 4.0 mm (blockout 3.75 x 3.8) centred at y = -1.0 mm; pin holes 4.2 mm
with 5.2 mm pads at x = +-21.8, +-11.45, 0 mm, y = -14.1 mm; corner radii 3.2 mm
(top) and 1 mm (bottom); mounting holes 1.2 mm at x = +-24.5 mm; buttons at x =
+-20.3 mm; speaker 8.5 mm square (consistent with an 8.5 x 8.5 x 3 mm magnetic
transducer, not confirmed); processor 6.5 mm, interface chip 5.0 mm, accelerometer
2.0 mm; USB 7.7 x 5.6 mm with 1.25 mm overhang (bounding box 43.25 mm in Y);
JST 8.3 x 6.0 x 5.5 mm; reset 6.0 x 5.8 mm. The microphone's port hole is drawn
on the lid and as a ring on the LED face; which side the real port faces is not
confirmed. Edge connector: 14 narrow fingers per face at 1.27 mm pitch (the real
board has more, narrower fingers).
