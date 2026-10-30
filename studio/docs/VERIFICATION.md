# Verification record — 2026-10-30

This record describes implementation verification, not certification of generated assets.
The current capability boundary is summarized in [STATUS.md](STATUS.md), with a
[machine-readable receipt](verification-20261030.json). Full local
commands, failed probes, review reports and logs are retained under
`.superpowers/sdd/2026-10-30-unified-3d-lab/`; that directory is deliberately excluded
from public gallery output. No private consumer source was copied.

## Environment and evidence

- WSL/Linux, Python 3.14.4; CI targets Python 3.12.
- Node 24.22.2, npm 10.9.9; dependencies pinned in the frontend lockfile.
- Blender CPU tests use the existing bpy 4.2 runtime, without modifying its environment.
- Chromium uses software rendering for functional checks. This is not a hardware performance benchmark.
- The repository's original library contains 1,152 models and six display variants at this branch's base.

## Established checks

| Check | Observed result |
| --- | --- |
| Existing creation Python contracts | 43 tests, 3 optional runtime skips; no failures |
| Existing Blender web bridge contracts | 4 tests, 1 optional runtime skip; no failures |
| Existing rigging Python contracts | 26 tests, 6 optional GPU/runtime skips; no failures |
| Gallery selection | 8 tests passed |
| Reference rights/family preservation | 7 tests passed |
| Portable educational benchmark | 18 tests passed |
| Portable benchmark artifacts | 10 runs / 287 files restored; 10 GLBs, zero Khronos errors or warnings |
| Preserved Claude/school archives | 9 Claude archives and two school conditions verified; historical quality verdicts preserved |
| Vendored source verification | 255 pinned sources passed |
| Skill entrypoints | 13 skills / 84 local links passed, plus application checks of the three new routes |
| Gallery publication boundaries | Static build and integrity/credential/path checks passed; Studio excluded |

The first integrated Studio run had 63 passing tests and one cleanup-completion race.
That failed log and the 20 diagnostic probes are retained. The final correction wave
covers that race, exact archive-byte validation, animation endpoints, mechanical
control linkage, capture metadata and JSON timeout errors. The final suite passes 72 Python tests (including real CPU Blender), 23 runtime tests
and 11 browser tests. Type checking, build and the production preview/capture smoke
also pass. The final review verdict is recorded in STATUS.md.

## Provider and engine boundaries

Native Meshy and Magnific account checks returned structured responses using free
balance tools. No account amounts or identifiers are included here. The checks prove
connectivity only. No paid generation, provider rigging or animation was submitted.

Blender rigid export/save/reopen/reimport and an explicit compatible humanoid retarget
were exercised on CPU, including a GLB target and rejection of incompatible metadata
and transforms. Those results do not approve an organic production character's
appearance, contacts or deformation.

UniRig integration delegates the existing laboratory runner, preserving its lock,
normalization and restoration. No new inference was run. SkinTokens has a pinned
isolated local/SSH adapter; the local 8 GiB GPU does not satisfy its 14 GiB preflight.
Local and remote SkinTokens inference remain BLOCKED / NOT_RUN respectively.

## Review and delivery

Task reviews used independent Sol contexts. The whole-branch review requested Astra
with high reasoning; implementation corrections requested Sol with high reasoning.
Actual backend model identifiers were not exposed, so these are requested profiles,
not measured model identity or benchmark results. The user explicitly authorized
parallel agents and model selection for this implementation.

The work is retained on `codex/unified-3d-lab`, with its worktree and experiments.
There is no main merge, push, deployment or remote GitHub Actions result for this cut.
The updated workflow runs offline Studio and browser checks alongside the existing
checks when a pull request or main push triggers it.