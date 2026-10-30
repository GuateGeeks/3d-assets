# Authoring scenes

The preview is a local, reusable scene viewer. Build it from studio/web with npm ci followed by npm run build. The output directory is studio/web/dist. npm run dev binds to 127.0.0.1; open the printed local URL. Add ?scene=scene.json to load a JSON scene, or use Load scene. The bundled workbench is the default.

Node.js >=22.12 is required by the pinned toolchain. This implementation was exercised with WSL Node 22.23.4. Node 24 is the recommended CI profile. Dependencies are exact versions in package.json and package-lock.json; the browser uses no CDN.

## Scene format

See studio/examples/interactive.scene.json and character.scene.json. All transforms are required XYZ triples: position in metres, rotation in radians, and positive scale. Root transforms belong to the scene; factories animate their own children.

schemaVersion is 1; kind is scene; id and title are strings; duration is seconds in (0, 300]; mode is interactive or timeline. IDs match ^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}$ and title must be nonempty. instances is an array (1–100) of unique id, asset, position, rotation, scale. Assets are button, servo, character, or a relative self-contained .glb path. GLB paths resolve relative to the scene JSON URL. Scene URLs must share this server's origin. No executable module can be provided in JSON; GLB external buffer/texture references are rejected.

tracks is optional. Each track has target (instance id), channel (pressed or angle), and strictly increasing keyframes with time in scene seconds and numeric value. pressed ranges from 0 to 1 and belongs to button; angle ranges from -180 to 180 degrees and belongs to servo. Values interpolate linearly and clamp to first/last keys. Duplicate tracks for a channel are rejected. Timeline owns tracked channels; interactive mode permits direct input. Button input releases on pointer-up, cancel, lost pointer capture, key-up, element blur, window blur and scene teardown.

The character built-in is an original articulated SkinnedMesh with seven named bones and Wave/Idle clips. original-character.glb is the equivalent original GLB sample; see PROVENANCE.md. A GLB's first clip is selected initially; the inspector can select another. Clip time and channels are evaluated from absolute scene time, including backwards seeks. Bone or clip channels are not accepted in JSON version 1.

## Controls and inspection

Choose objects in the object list, via labels, or by clicking geometry. Drag the canvas to orbit and scroll to zoom. The inspector exposes momentary button and servo slider controls; timeline-owned channels disable direct input. Playback has play/pause, reset, scrub, speed (0.5/1/2), and loop. Reduced-motion preference prevents automatic playback; explicit seeking remains available. Allow motion opts into playback during this session.

View options provides anchors, world-space bounds, the real rig helper, live WebGL draw-call/triangle counters, and Capture PNG. Counters describe the rendered frame and do not establish hardware performance budgets. Frame scene fits the visible assets. PNG capture downloads the current rendered canvas without UI.

mountPreview(host) from src/preview.ts mounts the complete viewer and returns an idempotent unmount callback. One requestAnimationFrame scheduler advances animation and rendering. The runtime uses analytical absolute-time evaluation, not a physics simulation: frames accumulate the full elapsed seconds without a silent delta cap, then sample tracks and clips at the resulting time. Equal total elapsed time partitioned across frames produces the same pose (within floating-point precision). Backgrounding pauses playback; no catch-up simulation is implied. Scene swaps prepare a replacement before disposing the current assets, and stale async results are discarded. Resource scopes count shared GPU resources, release geometry/material/texture/skeleton resources, and dispose late async allocations. Unmount removes listeners/ResizeObserver, cancels pending loads and the scheduler, disposes OrbitControls/renderer/assets and releases the WebGL context.

## Verification

npm test runs deterministic core tests. npm run typecheck checks TypeScript. npm run test:browser runs real Chromium controls, motion preference, mount/unmount, race handling, GLB skeleton/clip roundtrip, overlays, capture and scene swap tests. npm run build checks types and creates relative-path production assets. Install its browser using npx playwright install chromium. Ubuntu 26.04 currently requires PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64 for this pinned Playwright version. This compatibility override was tested with software rendering; it does not demonstrate hardware GPU performance.

To regenerate the original binary demo, start the dev server on port 5287 and run node scripts/generate-demo-glb.mjs from studio/web. PREVIEW_URL can select another local dev server. Regeneration is explicit and writes the two owned demo copies. External GLB authoring must preserve metres and embed buffers/textures. The viewer does not normalize or rescale imported models implicitly.

The Python preview command serves a selected project under /project/. Use ?scene=project/scene.json there. The browser resolves a project asset such as assets/robot.glb under that same project directory.
