# Studio status — 2026-10-30

Implemented on `codex/unified-3d-lab`; independent final correction review passes
spec compliance and code quality. All six final findings are addressed. See the
[verification record](VERIFICATION.md) for preserved checks, environments and limits.

| Capability | Current evidence |
| --- | --- |
| Contracts, project/run records, preview and package gates | 72 Python tests pass, including actual CPU Blender tests. Archive output hashes the exact bytes written; separate reviews bind the full inventory |
| Meshy/Tripo jobs | 26 provider fixture/persistence tests included above; request, authorized intent, receipt, unknown-outcome reconciliation, resume and GLB intake implemented |
| Provider connectivity | Free native Meshy and Magnific account checks returned structured responses; no paid generation, rigging or animation executed |
| Interactive objects and scenes | Original button drives servo; safe declarative bindings, channel ownership, reset/release and analytical absolute-time playback. No physics engine |
| Browser runtime | Node 24.22.2: 23 unit tests, 11 Chromium browser tests, TypeScript and production build passed |
| Original skin and clips | Seven-bone character, Wave/Idle clips and GLB roundtrip tested; endpoint hold and backward seek covered |
| Production preview | Loopback Python server with inventoried project passed build/CSP, ownership, timeline and capture checks; zero browser errors |
| Captures | Paired PNG/SHA-256 receipt records scene state, camera, viewport/DPR and renderer/runtime; [final view](../web/evidence/production-20261030/overview.png), [receipt](../web/evidence/production-20261030/capture.json), [smoke](../web/evidence/production-20261030/smoke.json) |
| Blender | Real bpy 4.2 CPU rigid export/save/reopen/reimport and explicit humanoid motion mapping pass, including GLB target, FPS/units/effective-transform rejection and hash lineage |
| UniRig | Existing candidate runner/lock/restoration delegated and tested; no new GPU inference in this cut |
| SkinTokens | Pinned isolated local/SSH adapter and memory preflight implemented. Local 8 GiB GPU is below required 14 GiB: BLOCKED. Remote GPU inference NOT_RUN |
| Publication | Integrated current main with 1,173 models and six display variants. Gallery build/path/credential checks pass and exclude Studio. Deployment remains manual |

The final production JavaScript bundle is approximately 643 KB before compression;
Vite reports its size warning. Hardware performance is NOT_RUN; software-rendered
browser tests are functional evidence only. No new organic asset receives production
visual/deformation/contact approval from these implementation tests.

Desktop, mobile and rig captures from the initial implementation remain preserved
alongside the final production view. Final production image and metadata were opened
and checked; the capture receipt is evidence, not an automatic visual PASS.
Historical UniRig corpus issues and benchmark verdicts remain unchanged.

## Push and merge preparation — 2026-10-30

Current main was merged into the Studio branch without conflicts, preserving the
new Poly Haven collection and both histories. The combined tree passed 72 Studio
Python tests (including CPU Blender), nine reference-policy tests, and the rebuilt
gallery integrity/path/credential checks. The original implementation receipt above
remains a historical snapshot; hosted CI is checked through the integration PR.

## micro:bit V2 interactive model — 2026-10-31

An original micro:bit V2 board (`studio/examples/microbit/microbit.glb`) driven by a
trusted Studio factory: buttons A and B, the touch logo and 25 individually lit LEDs,
resolved by glTF `extras.part_id` through `studio/examples/microbit/node-contract.json`.
Model made with the lab's iterative flow in `claude` mode; design in
`docs/superpowers/specs/2026-10-30-microbit-v2-interactive-design.md`; model record in
the [experiment README](../../creation-lab/experiments/microbit-v2/README.md) and
[PROVENANCE](../examples/microbit/PROVENANCE.md). The four verdicts below are separate;
none stands in for another. Vocabulary: `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`.

| Gate | Verdict | What it rests on |
| --- | --- | --- |
| Technical | PASS | Counts below, `check_contract.py` PASS (46 parts, 25 distinct LED materials, size within `displayScale`), run 003 technical PASS (46 meshes, 22,560 triangles, 43 materials, GLB 1,117,164 bytes, reopen and reimport PASS, Blender 5.2.3 LTS). The GLB sha256 is `b12143d94deda3faaae36c154bc2177a5c9f1c6deccb102947d5e27a7fe13687`, identical in `studio/examples/microbit/`, `studio/web/public/microbit/` and the lab run |
| Visual | PASS (third review) | Three fresh-context reviewers judged product captures at the viewer's default camera: round 1 FAIL, round 2 FAIL, round 3 PASS. Verdicts and reasons in the [review records](../web/evidence/microbit-visual-reviews/README.md). The lab review of the Blender renders (run 003, visual PASS) is a different judgement of different images |
| Content | PASS (third review) | The round-3 reviewer's content PASS (heart 16, smile 7, check 5 LEDs recognisable without zooming and matching the receipt channels), plus the lab content PASS for run 003 (all six brief checks PASS). Rounds 1 and 2 were content FAIL |
| Provenance | PASS (self-assessed: no independent rights review) | Original geometry by GuateGeeks, MIT; outline from the official V2.2 hardware page (51.60 x 42.00 x 11.65 mm); reference photos used for proportions only, not included here; no BBC or micro:bit logo, FCC ID or silkscreen text; component positions and sizes are estimates, flagged as such. Reviewer identities are requested, not confirmed (below) |

### Technical evidence (run in this session, Node 22.23.4, Python 3.14)

| Check | Result |
| --- | --- |
| `npm run typecheck --prefix studio/web` | passes, no errors |
| `npm test --prefix studio/web` (vitest) | 144 passed, 6 files |
| `npm run test:browser --prefix studio/web` (Playwright, software WebGL) | 43 passed |
| `npm run build --prefix studio/web` | builds; the JavaScript bundle is 654.91 kB before compression (Vite's size warning remains) |
| `python3 -m unittest discover -s studio/tests -v` | 80 tests OK, 4 skipped (the real CPU Blender tests need `STUDIO_BPY_PYTHON`, which this run did not set) |
| `python3 -m unittest discover -s creation-lab/tests -v` | 100 tests OK, 4 skipped (the real Blender tests need `CREATION_TEST_BLENDER`, not set in this run) |
| `python3 tools/check_skills.py` | PASS, 13 skills, 85 local links |
| `python3 creation-lab/registry/verify_sources.py` | PASS, 255 files verified (`runtimeExecuted` false) |
| `python3 creation-lab/experiments/microbit-v2/check_contract.py studio/examples/microbit/microbit.glb` | PASS |

The skipped tests are Blender-gated; the Blender runs for this model were executed
earlier in the lab session and are recorded in the experiment README, not re-executed
here. The older 72-test count in the table above is a historical snapshot; the counts
here are the current ones.

### Visual evidence

| Round | Evidence folder (unmodified, as reviewed) | Visual | Content | Verdict record |
| --- | --- | --- | --- | --- |
| 1 | [`microbit-20261031`](../web/evidence/microbit-20261031/README.md) | FAIL | FAIL | `r1-studio-visual-review.json` |
| 2 | [`microbit-20261031-r2`](../web/evidence/microbit-20261031-r2/README.md) | FAIL | FAIL | `r2-studio-visual-review.json` |
| 3 | [`microbit-20261031-r3`](../web/evidence/microbit-20261031-r3/README.md) | PASS | PASS | `r3-studio-visual-review.json` |

The records live in [`microbit-visual-reviews/`](../web/evidence/microbit-visual-reviews/README.md)
with their sha256. Round 1: lit LEDs were pale pink against off-white unlit LEDs, so
the patterns were not readable. Round 2: the LED look was fixed but the default camera
was low, off-axis and small. Round 3: the authored camera (elevation 62, azimuth 0)
fills about 73 % of the canvas width and the three patterns read without zooming.
All three reviewers are recorded as actor `unknown-subagent-fresh-context`, model
`claude-opus-5-5`, effort `medium`, as requested and unconfirmed by the runtime;
fresh context is not backend attestation. The lab runs were reviewed the same way
(reviews of runs 001 and 002 BLOCKED/BLOCKED then PASS/PASS; run 003 PASS/PASS).

### Rulings taken during the work

1. A `claude` authoring mode was added to `iterate.py` (exact Claude model IDs, explicit
   choice; the Sol/Luna default is unchanged).
2. An optional per-run `--extra-view` (`underside`, `top-down`) was added to the
   iterative flow, because the six standard views never show the underside of a flat
   board, so parts on the back could not be judged. It relaxes no rule: a hidden or
   unclear part still cannot pass.
3. After the failed visual reviews, the LED rest and lit look (dark package, red
   emissive, intensity from the brightness value) and an authored scene `camera` field
   were added on the Studio side only: no new Blender run, the GLB unchanged (sha256
   above), so the lab verdicts do not cover the LED look.
4. The last lab correction (1 of 2 used) was deliberately left unspent.

### NOT_RUN

- GPU performance (all rendering evidence is software, headless Chromium with SwiftShader).
- Live MakeCode simulator wiring: the patterns come from authored `patternBindings` and
  `tracks`, stand-ins for a future feed, not simulator output.
- Real multi-touch hardware.
- Any competency, learning-outcome or curriculum claim.

### Known non-blocking defects (from the reviews)

- No A/B or pin (0, 1, 2, 3V, GND) markings on the board, so a student cannot read
  which button is A from the model alone.
- The PCB renders slate grey rather than near-black.
- The edge connector has 14 fingers against about 20 on the real board, none outside
  pins 0 and GND; the gold ring around each pin hole is about 0.6 mm against about
  1 mm; a small dark component on the back touches the reset housing and the battery
  socket wall.
- No contact shadow, and only horizontal ground-grid lines; the board sits low in the frame.
- B pattern: the mouth corners are as bright as the eyes; only the bottom three mouth
  LEDs are dimmer.
- In the close-up, the Board label partly covers a lit LED and the overlay texts have
  low contrast.
- The 0.5 mm button travel is not visible at the default camera (the logo tint is).
- The lab reviewer saw the speaker, microphone, processor, antenna and accelerometer
  only on the lab's underside render; per-LED materials, `part_id` uniqueness and LED
  index mapping rest on the technical gate, not on renders.

### What this does not show

These runs were authored and reviewed in `claude` mode with requested, unconfirmed
models. No benchmark was run, so they say nothing about quality or cost versus the
Sol/Luna profile, and the session's two-correction budget is not evidence of either
being better.
