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
