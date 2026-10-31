# micro:bit V2 Studio captures, 2026-10-31

Functional captures of the original micro:bit V2 model (`studio/examples/microbit/microbit.glb`, creation-lab run `003-9621bf5caaca`, see `studio/examples/microbit/PROVENANCE.md`) in the production preview.

**What these are.** Evidence that the production build, served by `python3 studio/studio.py preview --project studio/.local/projects/microbit --port 4395` from a project created with `studio.py project init microbit`, loads `?scene=project/scene.json`, fetches the GLB from the project inventory (byte-identical, sha256 `b12143d9...3687`, see `capture-summary.json`) and drives the LED pattern from real pointer and keyboard holds.

**What these are not.**
- They come from software rendering (headless Chromium, SwiftShader, 1440 x 1000 viewport, 1152 x 820 canvas). GPU performance is `NOT_RUN`.
- A capture is evidence, not a visual approval. No visual verdict is made here; an independent reviewer with the images opened must judge them.
- The LED patterns come from the scene's `patternBindings` (heart on A, smile on B, check on the logo), which are stand-ins for a future simulator feed. Live MakeCode simulator wiring is `NOT_RUN`.

Each folder holds a PNG (the canvas only, no UI) and the receipt JSON the app wrote with it. The receipt records the PNG's SHA-256 and byte count, the camera, overlays, channel values and scene; keep the pair together. `capture-summary.json` lists the checks the capture script ran (all `PASS`) and the console messages seen; the only one is Chromium's notice that the software WebGL fallback is deprecated (it comes from the SwiftShader launch flags).

| State | Interaction while capturing | Lit LEDs | PNG sha256 |
|---|---|---|---|
| `rest/` | none | 0 | `34b849acd8fdd7996fd4396a5284c8c6874e8e7b5ee652f16f349596f90ca1e4` |
| `a-held/` | mouse held on the A button | 16 (heart) | `7e6e8a5848c4db402502d3d0df683668173e518cf082668279fdeea37af9e21f` |
| `b-held/` | mouse held on the B button | 7 (smile) | `b2a70406031bbc16b347c70bed639befdbef4f4de5feb496bf54688d39613357` |
| `logo-held/` | mouse held on the touch logo | 5 (check) | `85438cf40f5e4f7ca316e4725c2cb01ed24216472245b1f20e87ff4531093ad6` |
| `closeup-a-held/` | wheel zoom to the minimum distance, keyboard Hold A, Anchors on | 16 (heart) | `c5d76056c921fe4ae72d00ed28fd5a9089bdd90724b2a5627ae5813803b72d39` |

`closeup-a-held/page-with-labels.png` (sha256 `315357d39f150b4e442fb814ca381af0ef288c654c78fbecf6b0931629b1866d`) is a whole-page screenshot of the close-up state: the capture PNG excludes the UI, so this one shows the part labels (Anchors on), the inspector readout and the focused, held Hold A control. It has no receipt of its own; the close-up receipt describes the same moment.

Regenerate with `PREVIEW_URL=http://127.0.0.1:4395/ node scripts/capture-microbit-evidence.mjs <directory>` from `studio/web` while the project preview is running. A new run writes new timestamped files and different hashes; do not overwrite reviewed evidence.
