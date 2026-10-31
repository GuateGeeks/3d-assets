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
PCB thickness (1.6 mm) and component coordinates are not published on those pages
and are estimated from photos (unconfirmed).

## Files

| File | Purpose |
| --- | --- |
| `brief.json` | Lab brief: parts = the node contract, `displayScale` 0.052 m +/- 2 %, budgets, blockout and content checks |
| `generator_blockout.py` | Blockout generator (`build()`), simple volumes at true positions; the later detail generator refines them |
| `check_contract.py` | Stdlib GLB checker: each `part_id` once, 25 distinct LED materials, size within `displayScale` |
| `../../tests/test_microbit_contract.py` | Tests for the checker and the brief (synthetic GLBs, no Blender) |

Blender conventions: metres, Z up, front -Y. The board lies flat, LED face +Z
(+Y in glTF), edge connector toward -Y (+Z in glTF), origin at the board centre
on the PCB mid-plane. LED `led_x_y`: x column, y row, origin top-left seen from the
LED face with the edge connector at the bottom.

## Running

From the repository root (WSL with the native Windows Blender, adapter from the
Claude animal-cell benchmark; it must be executable):

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
| `001-0c91b4d0cb9e` | blockout | `aff01f0d2db1ac83d`, `claude-sonnet-5-5` medium | PASS (46 meshes, 14400 triangles, 41 materials, 51.6 x 42.8 x 11.65 mm; `check_contract.py` PASS) | NOT_RUN (awaiting independent review) | NOT_RUN | `e134696aa431b3db921574c5c3206311f8c94f40edd7f41d9fac4a3ff28deaa9` |

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
The shared worker renders low, fixed cameras (`front` and `back` look along the board
at 0.10 elevation); the back-face parts (USB, reset, battery socket, speaker,
microphone) sit below the PCB and are not visible in any of the six images, so
their placement is verified from geometry and the contract checker, not from images.
Later tasks append the review, detail and Studio capture runs here.
