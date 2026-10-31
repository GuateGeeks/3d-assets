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
| `generator_blockout.py` | Blockout generator (`build()`), simple volumes at true positions, plates with clean Delaunay caps; the later detail generator refines them |
| `check_contract.py` | Stdlib GLB checker: each `part_id` once, each LED a single-primitive mesh on a material no other node uses, size within `displayScale` |
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
python3 creation-lab/iterate.py review-template --session SESSION --run RUN_ID --output NEW_TEMPLATE.json
python3 creation-lab/experiments/microbit-v2/check_contract.py SESSION/runs/RUN_ID/asset.glb
```

An independent reviewer context opens the six images and fills the template;
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

`render_extra_views.py` (sha256 `c2fac1322f7742c7e703c65db0bda811d4cd437d541dd088c36bbe61e34bd653`)
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

Later tasks append the review, detail and Studio capture runs here.
