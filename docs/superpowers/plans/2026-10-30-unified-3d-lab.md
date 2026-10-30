# Unified 3D Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. The user explicitly authorized parallel agents on 2026-10-30; independent tasks have disjoint file ownership.

**Goal:** Deliver the approved local code-first 3D authoring laboratory, with honest live-provider/GPU verification boundaries.
**Architecture:** Python stdlib orchestration wraps existing tools and records immutable runs. A TypeScript/Three.js preview consumes versioned scene records. Provider and local-engine adapters are separate modules sharing core path/run utilities.
**Tech Stack:** Python >=3.10, Node 24, pinned Three.js/TypeScript/Vite/Vitest/Playwright, existing Blender and UniRig environments.
**Spec:** ../specs/2026-10-29-unified-3d-lab-design.md (approved by user: Proceed with implementation).

## Global Constraints

- Preserve original models, source metadata, licenses, historical evidence and specialized workflows.
- Browser uses metres, Y up, +Z forward; Blender uses metres, Z up, -Y forward. Test conversion explicitly.
- One heavy GPU job at a time. No paid API submissions, GPU provisioning or deployment in this implementation run.
- Providers are MCP-mediated; CLI records actual tool receipts and never pretends it invokes chat-owned tools.
- SkinTokens live inference remains BLOCKED without an eligible >=14 GB NVIDIA executor.
- No private Arduino source/assets copied. Original generic examples only.
- Separate technical, visual, content and provenance gates; skipped verification is not PASS.

## Review Focus

- Untrusted artifact paths, symlinks and malformed manifests must never escape the selected workspace (Task 1).
- Unknown submission outcomes must not cause duplicate paid jobs; late/out-of-order receipts must not regress terminal states (Task 2).
- Root placement, transformed anchors, repeated mount/unmount and release-on-blur must remain correct (Task 3).
- Incompatible rigs, Blender versions, units and remote executor profiles must fail before destructive or costly work (Task 4).
- Preview/package inventories must exclude local credentials, private source and arbitrary filesystem paths (Tasks 1 and 5).

### Task 1: Core contracts, immutable runs, project/preview/package CLI

Owner: coordinator. Files: studio/core.py, studio/contracts/, studio/studio.py, studio/preview.py, studio/tests/test_core.py, studio/tests/test_preview.py, studio/__init__.py, studio/adapters/__init__.py.
Interfaces: core.read_json(path)->dict; write_json(path,data)->None (atomic); sha256(path)->str; checked_path(root,relative,must_exist=True)->Path (reject absolute/traversal/symlinks); create_run(workspace,operation,inputs)->Path; record_event(run,event)->Path (immutable); validate_glb(path)->dict. workspace is a Path; run directories contain run.json and numbered immutable event files.
CLI global args: --workspace Path defaults studio/.local; --config Path optional; parsed args.settings is the loaded configuration dict, args.workspace is Path. Adapter register_commands(subparsers) installs commands with args.handler callable returning JSON-serializable result. CLI emits JSON and nonzero exit for failures.
- [x] Add failing behavior tests for immutable runs, traversal/symlink rejection, malformed GLBs, scene validation, package gate enforcement and server allowlist.
- [x] Run python3 -m unittest discover -s studio/tests -p test_core.py -v and test_preview.py; observe missing implementation failures.
- [x] Implement core and CLI commands doctor, capabilities, project init, run list/show, validate, preview, package. Add schemaVersion=1 contracts for project/asset/rig/motion/scene/run/package with explicit provenance/coordinates and gates.
- [x] Run core/preview tests and end-to-end project init -> validate -> preview HTTP -> package refusal/acceptance tests.
- [x] Commit only owned files after checking diff.

### Task 2: Meshy/Tripo provider job adapter

Owner: provider agent. Files: studio/adapters/providers.py, studio/contracts/providers.json, studio/tests/test_providers.py, studio/docs/PROVIDERS.md.
Interfaces: register_commands(subparsers)->None; describe(settings:dict)->list[dict]. Uses Task 1 core utilities when useful; may implement standalone job helpers. All jobs stay in args.workspace. Exact CLI group is provider. Tool arguments are prepared, not invoked by repository code.
- [x] Write failing tests for zero-budget preparation vs authorized submission intent, exact transport/body/mesh constraints, persistent fingerprints, duplicate request detection, unknown submit reconciliation, task-ID binding, out-of-order/terminal receipts, bounded polling guidance, output hash intake and secret redaction.
- [x] Run test_providers.py to observe failures.
- [x] Implement capabilities for native Meshy and Magnific Tripo; request envelopes, submission intent, receipt/status intake, reconciliation, resume instructions, local output intake. No silent transport switch or inferred costs.
- [x] Run provider tests including realistic complete response fixtures. Record which checks use fixtures vs live calls.
- [x] Commit owned files, return full report with exact commands and interfaces.

### Task 3: Interactive objects, scene runtime and browser preview

Owner: web agent. Files: studio/web/**, studio/examples/**, studio/docs/AUTHORING.md. Do not edit Python, root .gitignore, skills or CI.
Interfaces: built output studio/web/dist with index.html; reads optional scene.json via ?scene=scene.json, falling back to bundled original demo. Scene schemaVersion=1, kind='scene', id/title, duration seconds (0<duration<=300), mode='interactive'|'timeline', instances array of {id, asset, position:[x,y,z], rotation:[x,y,z], scale:[x,y,z]}; assets button/servo/character built-ins or explicit GLB relative URL. tracks {target,channel,keyframes:[{time,value}]} where supported channels are pressed and angle. Extra typed fields may be added and documented. Built assets must be relative-path compatible. No arbitrary executable module URL from scene JSON.
- [x] Write failing runtime tests for deterministic seek, input/timeline channel ownership, transformed anchors, resources/shared late allocations, release/cancel/blur and reduced motion; browser tests for actual controls and scene load/swap.
- [x] Implement typed contracts, factories for original button and servo, original articulated character/rig demo or licensed asset path, fixed scheduler, semantic selection, controls, overlays and playback. Scene root ownership remains separate from local animation.
- [x] Implement reusable mount/unmount preview UI with clean controls and responsive canvas. Pin dependencies and install locally; do not copy private code or use CDNs.
- [x] Run typecheck, unit/browser tests and build. Open/inspect captures when tooling permits; preserve capture paths, no invented visual PASS.
- [x] Commit owned files; report Node/runtime requirements and available scripts.

### Task 4: Blender/UniRig/SkinTokens adapters and motion interchange

Owner: engine agent. Files: studio/adapters/local.py, studio/adapters/blender_worker.py, studio/adapters/retarget.py or related local-only modules, studio/contracts/skintokens-profile.json, studio/tests/test_local.py, studio/docs/ENGINES.md. Do not edit root core/CLI or existing lab engines.
Interfaces: register_commands(subparsers)->None; describe(settings:dict)->list[dict]. CLI group backend. Settings contain blender executable, unirig repositoryRoot/python paths, skintokens executor profile. Use args.workspace and core utilities. New isolated runs; preserve existing environments.
- [x] Write failing tests for explicit axis conversion, dry-run command validation, malformed skeleton maps, missing inputs, already-rigged vs static routing, unsuitable VRAM/config, unsafe SSH/profile paths and hash-bound result intake.
- [x] Implement real Blender subprocess export/reopen/clip inspection, rigid clip demo and one documented humanoid retarget mapping. Delegate UniRig only to real supported commands and preserve their receipts/lock. Use existing original checkout runtime by explicit config, not symlink/copy environment.
- [x] Verify current official SkinTokens CLI/commit and implement pinned profile, local/path and optional configured SSH execution/staging with preflight >=14 GB VRAM, exclusive heavy-job lock, bounded subprocesses and output hash checks. Do not download weights or run GPU inference without eligible environment.
- [x] Run CPU fixture tests and real Blender/bpy opt-in CPU probe with original checkout runtime if available; preserve evidence in new workspace only.
- [x] Commit owned files and report actual runtime tests vs BLOCKED/NOT_RUN.

### Task 5: Integrated skills, CI, documentation and independent review

Owner: coordinator after interface integration. Files: AGENTS.md, README.md, SETUP.md, .gitignore, .github/workflows/validate.yml, tools/check_site.py where needed, relevant .agents/skills entrypoints and new focused interactive/provider/scene skills, studio/README.md, studio/docs/STATUS.md.
- [x] Test all adapter command groups through studio/studio.py. Add integration tests only for uncovered cross-module behavior (scene schema parity, preview artifact selection, backend/provider intake into packages).
- [x] Scope Blender-only policies, preserve cotizador specialization and route new authoring/provider jobs/scenes. Add local configuration example, reproducible install/preview/test commands and capability status receipts.
- [x] Add normal CI for Python contracts, frontend typecheck/unit/browser build and publication exclusion. No paid/GPU jobs on push. Keep manual deployment unchanged.
- [x] Run existing suites from clean worktree, new Python suite, web tests/build/browser, skill/source checks and static-site publication validation. Report known unrelated failures rather than weaken gates.
- [x] Generate review diff package and dispatch fresh independent final reviewer; resolve material findings with regression tests.
- [x] Save verification receipts and commits, open working preview, report unavailable live-provider/SkinTokens checks accurately. No automatic deploy or unrequested main merge.
