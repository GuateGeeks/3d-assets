# Authoring scenes

The preview is a local, reusable scene viewer. Build it from studio/web with npm ci followed by npm run build. The output directory is studio/web/dist. npm run dev binds to 127.0.0.1; open the printed local URL. Add ?scene=scene.json to load a JSON scene, or use Load scene. The bundled workbench is the default.

Node.js >=22.12 is required by the pinned toolchain. This implementation was exercised with WSL Node 22.23.4. Node 24 is the recommended CI profile. Dependencies are exact versions in package.json and package-lock.json; the browser uses no CDN.

## Scene format

See studio/examples/interactive.scene.json and character.scene.json. All transforms are required XYZ triples: position in metres, rotation in radians, and positive scale. Root transforms belong to the scene; factories animate their own children.

schemaVersion is 1; kind is scene; id and title are strings; duration is seconds in (0, 300]; mode is interactive or timeline. IDs match ^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}$ and title must be nonempty. instances is an array (1–100) of unique id, asset, position, rotation, scale. Assets are button, servo, character, or a relative self-contained .glb path. GLB paths resolve relative to the scene JSON URL. Scene URLs must share this server's origin. No executable module can be provided in JSON; GLB external buffer/texture references are rejected.

tracks is optional. Each track has target (instance id), channel (pressed or angle), and strictly increasing keyframes with time in scene seconds and numeric value. pressed ranges from 0 to 1 and belongs to button; angle ranges from -180 to 180 degrees and belongs to servo. Values interpolate linearly and clamp to first/last keys. Duplicate tracks for a channel are rejected. Timeline owns tracked channels; interactive mode permits direct input on unbound channels. Button input releases on pointer-up, cancel, lost pointer capture, key-up, element blur, window blur and scene teardown.

`bindings` optionally contains up to 100 bounded mechanical relationships. Each has exactly
`source`, `sourceChannel: "pressed"`, `target`, `targetChannel: "angle"`, `released`
and `pressed`. The source must be a button and the target a servo; the two numeric
angles must be finite in -180..180 degrees. Each target has one binding owner.
This restricted one-way relationship cannot form cycles or execute code. It is
an analytical visual mechanism, with no electrical or physics simulation.

The original workbench binds Button to Servo: a hold rotates the visible horn to
90 degrees; release restores 0. The bound servo slider is disabled and names its
owner. Separate unbound servos retain their rotary slider. In timeline mode an
explicit target track takes precedence; otherwise the binding samples the source
button's current value (including its track). A seek applies tracks before bindings.
Interactive input cannot write a bound target. Mode changes release the button
when live input gains ownership; release/cancel/reset updates the linked mechanism.
Reset clears channels, then reapplies time-zero tracks and bindings, so a nonzero
`released` angle remains the authored resting pose.

The character built-in is an original articulated SkinnedMesh with seven named bones and Wave/Idle clips. original-character.glb is the equivalent original GLB sample; see PROVENANCE.md. A GLB's first clip is selected initially; the inspector can select another. Clip time and channels are evaluated from absolute scene time, including backwards seeks. Clips explicitly sample once and hold the final pose at and beyond their duration; the scene Loop option repeats scene time. Short clips do not implicitly repeat inside a longer scene. Bone or clip channels are not accepted in JSON version 1.

## Controls and inspection

Choose objects in the object list, via labels, or by clicking geometry. Drag the canvas to orbit and scroll to zoom. The inspector exposes momentary button and servo slider controls; timeline-owned and binding-owned channels disable direct input. Playback has play/pause, reset, scrub, speed (0.5/1/2), and loop. Reset pauses playback, clears every interactive channel to zero, restores the initial animation clip and pose, and seeks to time zero. In timeline mode, authored time-zero keyframes are reapplied. Reset preserves the current mode, root transforms and playback/view preferences. Reduced-motion preference prevents automatic playback; explicit seeking remains available. Allow motion opts into playback during this session.

View options provides anchors, world-space bounds, the real rig helper, live WebGL draw-call/triangle counters, and Capture PNG. Counters describe the rendered frame and do not establish hardware performance budgets. Frame scene fits the visible assets. Capture downloads a paired PNG and JSON receipt with a shared timestamp identifier.
The receipt binds the exact PNG SHA-256 and byte count to the scene specification,
current time/mode/channels/transforms/clip selections, camera projection/transform/
orbit target, CSS and drawing-buffer sizes, device and effective renderer DPR,
WebGL identity/settings, Three.js and preview versions, user agent and overlays.
It describes the frame at capture time, including during playback; it is evidence,
not a visual approval. Keep both files together. The PNG contains the canvas without UI.

mountPreview(host) from src/preview.ts mounts the complete viewer and returns an idempotent unmount callback. One requestAnimationFrame scheduler advances animation and rendering. The runtime uses analytical absolute-time evaluation, not a physics simulation: frames accumulate the full elapsed seconds without a silent delta cap, then sample tracks and clips at the resulting time. Equal total elapsed time partitioned across frames produces the same pose (within floating-point precision). Backgrounding pauses playback; no catch-up simulation is implied. Scene swaps prepare a replacement before disposing the current assets, and stale async results are discarded. Resource scopes count shared GPU resources, release geometry/material/texture/skeleton resources, and dispose late async allocations. Unmount removes listeners/ResizeObserver, cancels pending loads and the scheduler, disposes OrbitControls/renderer/assets and releases the WebGL context.

## Verification

npm test runs deterministic core tests. npm run typecheck checks TypeScript. npm run test:browser runs real Chromium controls, motion preference, mount/unmount, race handling, GLB skeleton/clip roundtrip, overlays, capture and scene swap tests. npm run build checks types and creates relative-path production assets. Playwright always starts and stops its own server (reuseExistingServer=false) on IPv6 loopback http://[::1]:5287; it refuses to reuse another application. The IPv6 test binding avoids the slow WSL connection timeout for an unbound IPv4 loopback port. Regular npm run dev continues to bind127.0.0.1. Install its browser using npx playwright install chromium. Ubuntu 26.04 currently requires PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64 for this pinned Playwright version. This compatibility override was tested with software rendering; it does not demonstrate hardware GPU performance.

To regenerate the original binary demo, start the dev server on port 5287 and run node scripts/generate-demo-glb.mjs from studio/web. PREVIEW_URL can select another local dev server. Regeneration is explicit and writes the two owned demo copies. External GLB authoring must preserve metres and embed buffers/textures. The viewer does not normalize or rescale imported models implicitly.

The Python preview command serves a selected project under /project/. Use ?scene=project/scene.json there. The browser resolves a project asset such as assets/robot.glb under that same project directory.

## micro:bit demo scene

studio/examples/microbit/microbit.scene.json (copy in studio/web/public/microbit/, open with ?scene=microbit/microbit.scene.json on the dev server) shows the original micro:bit V2 model, see studio/examples/microbit/PROVENANCE.md. An instance with behavior microbit loads its GLB through the trusted micro:bit factory, which resolves the 46 parts of studio/examples/microbit/node-contract.json by glTF extras part_id and exposes 28 channels: a, b and logo (0..1, momentary) and led.X.Y (X column, Y row, origin top-left, 0..255 like the MakeCode simulator). At load the factory applies the LED look from the contract, not from the GLB: `ledRest` (dark body `color` and `roughness`, because the exported LED packages are near-white and would wash out the glow) and `ledEmissive` (red `color`, `maxIntensity` at brightness 255 and `brightnessGamma`; emissive intensity is `maxIntensity * (brightness/255)^brightnessGamma`, so 80 reads clearly dimmer than 255 after the viewer's tone mapping). `patternBindings` (source a, b or logo; 5x5 released and pressed grids of 0..255) light LEDs while a part is held; overlapping patterns combine by per-LED maximum and interactive input cannot write a bound LED. `tracks` on led.X.Y replay a recorded LED sequence in timeline mode. The three patterns (heart, smile, check) and the 6 s sequence are generated by studio/web/scripts/generate-microbit-scene.mjs and are stand-ins for a future live feed from the MakeCode simulator; they are not simulator output. Run `node scripts/generate-microbit-scene.mjs` from studio/web to regenerate both scene copies.
