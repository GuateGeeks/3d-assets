# micro:bit V2 Studio captures, round 3 (authored opening camera), 2026-10-31

Functional captures of the original micro:bit V2 model (`studio/examples/microbit/microbit.glb`, creation-lab run `003-9621bf5caaca`, unchanged and byte-identical to rounds 1 and 2; see `studio/examples/microbit/PROVENANCE.md`) in the production preview, **after** the scene gained an authored `camera` (elevation 62 degrees, azimuth 0: the camera is on the +Z side looking down at the LED face, USB end at the top of the screen). The preview fits the board so it fills about 80 % of the canvas on the limiting axis. The earlier rounds, `../microbit-20261031/` and `../microbit-20261031-r2/`, were reviewed as FAIL and are kept unchanged; this folder is new evidence and replaces nothing. The top-down extra views of round 2 were not repeated (the authored view is now the default).

**What these are.** Evidence that the production build, served by `python3 studio/studio.py preview --project studio/.local/projects/microbit-r3 --port 4395`, loads `?scene=project/scene.json`, fetches the GLB from the project inventory (sha256 `b12143d9...3687`, see `capture-summary.json`), opens at the authored camera (every receipt records elevation 62.0 and azimuth 0.0 degrees, distance 0.0843 m; the close-up 0.0421 m) and drives the LED pattern from real pointer and keyboard holds.

**What these are not.**
- They come from software rendering (headless Chromium, SwiftShader, 1440 x 1000 viewport, 1152 x 820 canvas). GPU performance is `NOT_RUN`.
- A capture is evidence, not a visual approval. The author makes no visual verdict; an independent reviewer with the images opened must judge them.
- The LED patterns come from the scene's `patternBindings` (heart on A, smile on B, check on the logo), which are stand-ins for a future simulator feed. Live MakeCode simulator wiring is `NOT_RUN`.

Each folder holds a PNG (the canvas only, no UI) and the receipt JSON the app wrote with it (it records the PNG's SHA-256 and byte count, camera, overlays, channels and scene; keep the pair together). `capture-summary.json` lists the checks the capture script ran and the console messages seen; the only one is Chromium's notice that the software WebGL fallback is deprecated (it comes from the SwiftShader launch flags).

| State | Interaction while capturing | Lit LEDs | PNG sha256 |
|---|---|---|---|
| `rest/` | none | 0 | `ef932360a08bf22fec2a92fa38db2574f2a7c2a1aaa08bd26eb07759b8567ba9` |
| `a-held/` | mouse held on the A button | 16 (heart) | `859135a21d99725eadd6bcca90eab0ec4cb6db5780501c7e4059b732fd90199c` |
| `b-held/` | mouse held on the B button | 7 (smile) | `474f30a38b413149bff49140784910e162344f153991db4692f238364d1a02c9` |
| `logo-held/` | mouse held on the touch logo | 5 (check) | `626cdcbc3eababaec50f45c5b1ddd997e2041ebacbe37432ad2db3900630d214` |
| `closeup-a-held/` | wheel zoom to the minimum distance, keyboard Hold A, Anchors on | 16 (heart) | `256f05a2e0bebc91e54b0fc96e55edd6b26c23d7637fff28de27b18c7464a0e7` |

`closeup-a-held/page-with-labels.png` (sha256 `23b135b85a84dd60a1b7175dda3bf8db74ccf90320e6a7e442536af49a162931`) is a whole-page screenshot of the close-up state (part labels with Anchors on, inspector readout, focused Hold A control). It has no receipt of its own; the close-up receipt describes the same moment.

Regenerate with `PREVIEW_URL=http://127.0.0.1:4395/ node scripts/capture-microbit-evidence.mjs <directory>` from `studio/web` while the project preview is running (`CAPTURE_TOPDOWN=1` adds the optional top-down views). A new run writes new timestamped files and different hashes; do not overwrite reviewed evidence.
