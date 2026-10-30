# Studio status — 2026-10-30

Implementation checkpoint on `codex/unified-3d-lab`; integration review in progress.

| Capability | Current evidence |
| --- | --- |
| Contracts, project/run records, preview and package gates | Implemented; Python behavior tests exercise paths, symlinks, hashes, malformed data and exact-inventory reviews |
| Meshy/Tripo job adapters | Implemented; 26 offline fixture/persistence tests. No paid generation, live output or cancellation executed |
| Provider account connectivity | Free native Meshy balance and Magnific balance tools returned structured responses; amounts/account information omitted. This verifies account access only |
| Interactive runtime | 15 unit tests, 7 Chromium browser tests, TypeScript and production build passed on Node 22.23.4; analytical absolute-time playback, not a physics engine |
| Original example skin and clips | Seven bones, Wave and Idle clips; browser GLB export/load roundtrip tested |
| Browser visual inspection | Desktop, mobile and rig captures opened; [desktop](../web/evidence/desktop.png), [mobile](../web/evidence/mobile.png), [rig](../web/evidence/rig.png) |
| Blender adapter | Real bpy 4.2 CPU rigid export/save/reopen/reimport and explicit humanoid mapping fixture passed. No new organic rig visual approval |
| UniRig | Delegates existing candidate runner/lock/restoration; command and receipt handling tested. No new GPU inference in this cut |
| SkinTokens | Pinned isolated local/SSH adapter and preflight implemented. Local GPU 8 GiB is below required 14 GiB: BLOCKED. GPU/SSH inference NOT_RUN |
| Production performance | Hardware renderer benchmark NOT_RUN; browser software rendering is functional evidence only |
| Publication | No merge to main, push or deployment in this implementation cut |

The current frontend build reports an approximately 639 KB JavaScript chunk before
compression. The initial preview favors a small dependency surface and direct loading;
performance on target hardware needs a separate measured run.

Historical UniRig corpus issues and benchmarks remain unchanged. Review of old evidence
is not a new runtime verification. Credentials, private source and run artifacts remain
outside public inventory. Final receipts and review outcomes will be recorded when the
integration checks finish.
