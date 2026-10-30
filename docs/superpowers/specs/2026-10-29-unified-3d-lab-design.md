# Unified 3D Lab — code-first design

Date: 2026-10-29. Status: proposed design, pending document approval.
The user selected the recommended Codex-led workflow with a browser preview.
The detailed architecture below is the builder's proposal, not a claim that it is implemented.
Basis: [repository and provider audit](../../reviews/2026-10-29-3d-lab-audit.md).

## Intent and outcome

Create, edit, rig and animate reusable 3D objects and scenes through code and Codex, inspect the result locally, and keep reproducible evidence. Combine procedural Three.js, Blender, Meshy, Tripo, UniRig and SkinTokens through explicit adapters. Preserve the existing library, specialized workflows and experiments.

A user describes an object or scene. Codex prepares a measurable brief, chooses a supported route, produces a blockout, obtains the existing concept/blockout review when applicable, iterates within the declared budget, and opens a browser preview. The user can select objects, manipulate supported controls, inspect anchors and rigs, play/pause/scrub declared animations, and review evidence. Accepted outputs form local versioned packages. Public promotion remains a separate action.

“Best” means demonstrated usefulness and reliable interchange: editable source, functional interactions, reviewed visual quality, deterministic playback, preserved scale/materials, bounded performance/cost and reproducible delivery. It does not mean an unmeasured ranking above other tools.

## Approaches considered

1. **Code-first orchestration and browser preview — selected.** Builds on current Python CLIs, procedural JS, Codex skills and Blender tooling. Supports rich behavior as source code and asset interchange as separate deliverables. Requires an explicit common contract and adapters.
2. **Full visual editor with a scene timeline.** Adds direct manipulation and timeline authoring, but requires a substantially larger editor, persistence, undo, selection and authoring UX project. Playback controls are included now; a full editor is deferred.
3. **Blender as the sole authoring host.** Strong DCC editing and animation, but browser simulation, controls and JavaScript behavior would still require a separate runtime. Keep Blender as an integrated editor and exporter rather than the sole host.

## Scope and boundaries

Included: a local unified CLI, capability diagnostics, briefs/run records, generic interactive object and scene contracts, a browser preview, provider job receipts, Blender import/export and animation adapter, UniRig delegation, a separately configured SkinTokens adapter, scoped skills, tests and reproducibility documentation.

Excluded: a full timeline editor, cloud hosting, collaboration accounts, arbitrary Arduino C++ execution, automatic public catalog updates, automatic deployment, automatic GPU rental or model training. No mass migration or rewriting of historical runs. The Arduino app remains a consumer with a private adapter boundary; recovered assets and private source are not copied to public sources.

Keep the seven existing creation skills' review/provenance principles. Keep original models, metadata, hashes, corpus receipts and benchmarks immutable. A new result always gets a new run. Continue one heavy GPU job at a time and one editor per `.blend`.

## Repository layout and entry point

Add `studio/` as the integration layer, leaving `creation-lab/`, `lab/` and `procedural-web/` in place:

- `studio/studio.py`: Python stdlib CLI and local run orchestration.
- `studio/contracts/`: versioned JSON contracts, validation rules and migrations.
- `studio/adapters/`: provider/transport and existing-CLI adapters.
- `studio/web/`: TypeScript/Three.js runtime and browser preview; dependencies pinned by lockfile.
- `studio/examples/`: original reproducible object/scene examples with provenance.
- `studio/tests/`: contract, adapter-fixture and integration tests.
- `studio/.local/`: ignored configuration, runs, downloads and reports; never a publication input.

Proposed command groups: `doctor`, `capabilities`, `project`, `run`, `provider`, `preview`, `validate`, `package`. The implementation plan may refine subcommands, but documentation must use actual implemented commands. Existing CLI commands stay valid; the new layer invokes them with explicit config and records child-run references.

The local preview binds loopback and serves only the selected project/run and its allowlisted artifacts. It does not expose the repository, arbitrary paths, credentials or a general Python/JavaScript execution endpoint. Code authoring/build runs through the trusted local CLI; the preview executes only the selected project's built modules. Treat imported provider metadata as data.

## Asset, run and scene contracts

Use separate versioned records:

| Record | Required meaning |
| --- | --- |
| Project/brief | Goal, references, target runtime, dimensions, axes, style, budgets, inputs/rights, acceptance gates |
| Asset | Stable ID and revision, kind, source files/hashes, artifact paths, provenance, units/up/front, bounds, capabilities |
| Run | Unique ID, parent IDs, requested operation, adapter/version, inputs, logs, outputs, timestamps and separate gate results |
| Rig | Asset revision, skeleton hierarchy/rest pose/bind data, joint semantics, skin constraints, review evidence |
| Motion | Rig/skeleton profile, clip channels, duration/sample rate, root-motion policy, source/rights |
| Scene | Instances of asset revisions, transforms, assemblies/anchors, state/actions, tracks/events, cameras/lights and budgets |
| Package | Explicit reviewed inventory, source and runtime outputs, dependencies/licenses, checksums and validation receipts |

The browser uses metres, Y up, +Z forward. Blender uses its existing metres/Z-up/-Y-front convention. Every adapter declares and tests its conversion and inverse; source-specific mm-like units are never guessed or silently normalized. Mesh normalization for UniRig remains temporary and restores the whole hierarchy through the existing adapter.

Paths are relative to an allowed artifact root, hashes verified, and symlink/path escapes rejected at intake. Raw provider receipts remain local, sanitized before any distributable report. Executable source and runtime behavior are distinct from optional GLB/FBX artifacts. A GLB export must list omitted or baked behavior/material features.

## Interactive authoring runtime

Use a generic typed factory contract with `root`, local anchors, declared capabilities, typed state/actions, semantic picking, `update(time, delta, state)` and idempotent `dispose()`. Provide optional control descriptors for button, toggle, range and rotary input. The implementation chooses exact TypeScript signatures without Arduino state/domain imports.

The scene owns instance root transforms and transitions. Components animate children or declared channels. One scheduler supplies deterministic time; models do not create competing RAF loops, timers or simulation clocks. Scene state is the single source for preview controls, model behavior and any consumer adapter.

Separate fixed-step simulation from rendering and timeline playback. A reset/seek restores initial state and evaluates forward deterministically; bounded evaluation rules prevent unbounded work. Clip playback supports pause, seek, loop and speed. Define property ownership when a track and live input overlap: explicit scene mode selects timeline-driven or interactive-driven authority per channel; no last-writer race.

Track selection by semantic instance ID, not a mesh's transient name. Transform anchors correctly under parent translation/rotation/scale. On pointer release/cancel/lost capture, blur, unmount and scene change, release active controls. Keyboard interaction and reduced motion preserve functional feedback. Resource ownership must handle shared assets, late allocations and repeated mounting without leaks; the scene releases external resources it owns.

Deliver original examples: a pressable button, a rotary actuator/servo, and a small mechanical learning scene linking the button and rotary control to moving parts. Add one articulated character/creature scene using an appropriately licensed existing asset or a separately approved generated result. These validate different paths; the mechanical scene is not a deformation benchmark.

## Browser preview

An inspection surface, not a general editor: object/scene selection, orbit camera, reset, declared controls, anchors/bounds/rig overlays, clip selector, play/pause/seek, reduced motion, diagnostics and links to run evidence. Record viewport, camera, renderer, device pixel ratio and relevant runtime versions in captures. Build reusable mount/unmount APIs rather than an anonymous-listener single-page demo.

Use the lab's own renderer and original UI. Do not reproduce private Arduino compositors or fonts. Optional private consumer adapters load only from explicitly configured local workspaces, are excluded from packages by default, and are not dependencies of public CI.

## Provider integration and resumable jobs

A provider definition identifies provider, transport and adapter version. Operation descriptors declare supported formats, body types, limits, models, skeleton profiles and output semantics. Track `implemented`, `configured`, `session-exposed`, and `last-verified-receipt` separately; an unavailable feature is visible with its reason.

First transport: Codex-managed MCP for available Meshy/Magnific tools. A repository command prepares and persists a validated request envelope; Codex calls the selected tool and records the real receipt/task ID through a strict intake command. Polling and downloading similarly attach actual receipts and outputs. The CLI does not pretend it can call a chat-owned MCP tool itself. A new chat can resume using recorded identifiers after rediscovery; lack of the connector is an explicit BLOCKED state.

Use native Meshy MCP where its tools cover the operation. Use Magnific for Tripo operations exposed there. Do not silently switch accounts/transports or translate their credit units. Direct API transport is an extension point, not a required initial implementation; unsupported Tripo retarget operations remain unavailable through this transport, while the Blender animation path provides scene animation.

Persist request fingerprints and input hashes before submission. Record remote task ID/type immediately. Preserve parent task IDs, raw/normalized status, errors, model version, actual reported cost and output hashes. A submission with unknown outcome enters reconciliation-required state; do not automatically resubmit. Retry status polling/downloads with bounded backoff. Cancellation is best effort, with no assumed refund. Remote URLs are temporary; download authorized outputs promptly and validate before promoting to an Asset record.

Default paid budget is zero. Build/configure and fixture-test adapters without spending. Before a live paid canary, present the exact operation/provider, inputs, expected credit cost and ceiling; existing authorization applies only within its stated scope. Additional unapproved stages or retries stop before submission. No credentials in browser bundles, source or logs.

## Blender, rigging and animation

Blender adapter owns its process/scene and writes new run artifacts; it does not edit an unrelated open scene. Preserve native Blender and UniRig bpy environments separately. Use GLB between incompatible Blender versions. Keep the cotizador rigid 12-bone bridge as a specialization, not a universal conversion target.

For rigid/mechanical objects, use pivots and transforms. For organic meshes, choose a capable rig adapter. UniRig delegates to the existing pinned runner and lock; its static ingestion contract is unchanged. Imported already-rigged assets follow a separate validation path. Never discard a rig or animation merely to satisfy static intake.

SkinTokens gets a pinned isolated executor profile and adapter with preflight, request/result manifests and a smoke fixture. Default execution remains unavailable on this 8 GB host. Support a user-configured local/path or SSH executor with at least the documented 14 GB NVIDIA VRAM; no automatic provisioning. An SSH profile has a fixed host/work directory, explicit staged inputs, checked output paths/hashes and shared heavy-job locking. Remote integration is not called verified until a real execution receipt exists. Exact upstream commit/environment selection belongs to implementation research and must be pinned before install.

Keep rig creation, motion creation and retargeting separate. Meshy animation consumes a Meshy rig task ID; other rigs cannot masquerade as one. Cross-skeleton motion uses an explicit Blender mapping/rest-pose adjustment and records the source/target skeleton hashes, axes, scale and root-motion policy. Initial retarget support is one documented humanoid mapping plus rigid transform clips; other topologies are capability-gated until mapped and tested.

Review anatomy, weights, limits, foot/contact behavior, root motion and swept bounds before labeling an animated output accepted. Bake supported tracks for interchange, reopen in a clean process, compare selected poses and clip metadata, and inspect actual playback. Keep runtime interactions as module/scene data beside any baked GLB.

## Skills and configuration integration

`gg3d-pipeline` becomes the common router. Scope the existing Blender iterative workflow and static QA to their paths. Keep cotizador skills specialized. Add focused instruction routes for generic interactive authoring, provider jobs, and animated scenes; filenames and exact split may be chosen in the implementation plan.

Do not copy whole chat histories or duplicate policy across skills. Keep one capability inventory and one shared acceptance policy, with links to backend-specific commands. Separate author/reviewer model preferences from provider accounts, runtime paths and job budgets. Use versioned examples and ignored local configuration, resolved with explicit CLI overrides and diagnostics; no global settings changes.

The Arduino lessons become generic contracts and verification techniques implemented independently. A separate private consumer may adapt Arduino types. Neither private code nor assets with unresolved redistribution terms enter public sources or default packages.

## Validation and delivery sequence

1. **Common foundation and offline interactive slice.** Contracts, CLI/run store, diagnostics, skills routing, browser runtime, original button/rotary objects and assembled scene. Acceptance: deterministic state/seek, correct anchors/transforms, picking/keyboard/cancellation, reduced motion, teardown and viewed browser evidence.
2. **Provider intake and Blender interchange.** Meshy/Tripo request/receipt adapters with fixtures, real downloadable artifact intake, Blender reopen/export, and cost/resume safeguards. A live provider canary requires approved credits and credentials; fixtures are reported separately.
3. **Rig and scene animation.** UniRig integration, imported-rig path, one humanoid retarget mapping, scene playback, baked clips and reviewed deformation/contact evidence. Preserve known corpus issues until corrected in new variants.
4. **SkinTokens execution and comparative evidence.** Implement isolated profile/adapter and test preflight locally; run on a suitable configured executor when supplied. Compare the same source/poses with UniRig using separate technical/visual/content decisions. Do not claim superiority from one sample.
5. **Reproducible handoff.** Clean-clone checks, docs/skills/config verification, package inventory, CI receipts and explicit list of unavailable/live-unverified capabilities. No deployment.

Normal GitHub CI remains free of paid APIs and GPU assumptions. Add schema/CLI/adapter-fixture tests, TypeScript checks, runtime unit tests, browser lifecycle/scene tests and original example builds. Keep all existing gallery, source-lock and evidence restoration checks. Use manual opt-in Blender/GPU/live-provider verification with receipts; skipped stages remain NOT_RUN or BLOCKED, never PASS.

For each route retain independent gates: structure/compile, technical behavior, visual quality, content correctness and provenance. Open comparison images before visual verdicts. Final acceptance includes clean reopen/reimport where relevant, repeated mount/swap checks, critical animation states, full-frame performance budgets on the measured renderer, and a distributable explicit inventory. A successful process alone is not asset approval.

## Builder discretion and remaining external prerequisites

The builder may choose small internal module boundaries, exact CLI subcommands, schema validation implementation, pinned frontend test versions and preview styling consistent with the approved architecture. New direct API transports, a full visual editor, automatic public publishing or weakening gates are scope changes.

Live paid verification needs a budget; SkinTokens live verification needs an eligible executor. These do not block implementing and testing the offline foundation. Implementation must report those boundaries explicitly rather than silently reducing the requested integration to documentation or unexecuted placeholders.

## Design review record

A separate Sol medium reviewer read this design in a fresh context on 2026-10-29 and reported “nothing important left” for implementation planning. This is a design completeness review, not approval from the user or verification of implemented software. Local document links and the existing skill-link checks passed after writing this design.
