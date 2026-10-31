# micro:bit V2 Studio captures, round 2 (LED look fix), 2026-10-31

Functional captures of the original micro:bit V2 model (`studio/examples/microbit/microbit.glb`, creation-lab run `003-9621bf5caaca`, unchanged and byte-identical to round 1; see `studio/examples/microbit/PROVENANCE.md`) in the production preview, **after** the Studio factory started applying the LED look from `node-contract.json` (dark body `#1a0e0d`, roughness 0.6, emissive `#ff2a1a`, maximum intensity 1.2, brightness gamma 1.5). The first round, `../microbit-20261031/`, was reviewed as FAIL on LED legibility and is kept unchanged; this folder is new evidence and replaces nothing.

**What these are.** Evidence that the production build, served by `python3 studio/studio.py preview --project studio/.local/projects/microbit --port 4395`, loads `?scene=project/scene.json`, fetches the GLB from the project inventory (sha256 `b12143d9...3687`, see `capture-summary.json`) and drives the LED pattern from real pointer and keyboard holds.

**What these are not.**
- They come from software rendering (headless Chromium, SwiftShader, 1440 x 1000 viewport, 1152 x 820 canvas). GPU performance is `NOT_RUN`.
- A capture is evidence, not a visual approval. The author makes no visual verdict; an independent reviewer with the images opened must judge them.
- The LED patterns come from the scene's `patternBindings` (heart on A, smile on B, check on the logo), which are stand-ins for a future simulator feed. Live MakeCode simulator wiring is `NOT_RUN`.
- The `topdown-*` captures are an extra evidence view, reached by mouse-orbiting to the camera's upper limit (receipt elevation 90 degrees). They are not a product default; the default camera is the oblique one in `rest/`.

Each folder holds a PNG (the canvas only, no UI) and the receipt JSON the app wrote with it (it records the PNG's SHA-256 and byte count, camera, overlays, channels and scene; keep the pair together). `capture-summary.json` lists the checks the capture script ran and the console messages seen; the only one is Chromium's notice that the software WebGL fallback is deprecated (it comes from the SwiftShader launch flags).

| State | Interaction while capturing | Lit LEDs | PNG sha256 |
|---|---|---|---|
| `rest/` | none | 0 | `881665bcc4d1dbfb047c92e201ea55b86b55bbc7acf7e869c4344f083292f4f0` |
| `a-held/` | mouse held on the A button | 16 (heart) | `d61638c59f6f24ee93da5900e439d0630bafe6560f24ef4514dd00ae437e90cf` |
| `b-held/` | mouse held on the B button | 7 (smile) | `af38c327a9112736a62d10a01b6869fb740360358ef2e3717bc5d76043a28661` |
| `logo-held/` | mouse held on the touch logo | 5 (check) | `674a931e115826497c3d2f821a4bdb2dcc75a58835a445fc945ea297550d0d7a` |
| `topdown-a-held/` | EXTRA VIEW: orbited to look straight down at the LED face, keyboard Hold A | 16 (heart) | `71b78d577de3a83acb633b34f284582604ad734d28cf25ec1950658a3883a2d0` |
| `topdown-b-held/` | EXTRA VIEW: same top-down camera, keyboard Hold B | 7 (smile) | `c352c3c808fd4c5e8306047a63ba1bbfcb885e4d37eace72c6706eb5aeaa8bb8` |
| `topdown-logo-held/` | EXTRA VIEW: same top-down camera, keyboard Hold logo | 5 (check) | `5671c22b5f821f001e26463c7a47051b34ffb2e9ae68bdbd7b3b2749b2546dbb` |
| `closeup-a-held/` | wheel zoom to the minimum distance, keyboard Hold A, Anchors on | 16 (heart) | `b1e80feb0ed4ba3a083c215177b96e70963a3e675dcdcd5c10bc219fc78249e9` |

`closeup-a-held/page-with-labels.png` (sha256 `326eda53e0f55935ac824f88c33520e5d4b9afe9ec68a7a02f874dff3cdf7bc4`) is a whole-page screenshot of the close-up state (part labels with Anchors on, inspector readout, focused Hold A control). It has no receipt of its own; the close-up receipt describes the same moment.

Regenerate with `PREVIEW_URL=http://127.0.0.1:4395/ node scripts/capture-microbit-evidence.mjs <directory>` from `studio/web` while the project preview is running. A new run writes new timestamped files and different hashes; do not overwrite reviewed evidence.
