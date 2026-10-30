# Provider jobs

The `provider` CLI prepares exact MCP tool arguments and records externally obtained receipts. It makes no network requests, invokes no chat-owned MCP tool, and spends no credits. The default paid budget is zero. Capability descriptors separate implementation, configured account hints, session exposure hints, and the last externally verified receipt. Settings alone do not establish connector availability or a successful live call.

Supported initial routes:

| Provider | Transport | Operations |
| --- | --- | --- |
| Meshy | `native-mcp` | `text-to-3d`, `image-to-3d`, `remesh`, `rig`, `animate` |
| Tripo | `magnific-mcp` | `text-to-3d`, `image-to-3d`, `remesh`, `rig` |

Tripo animation/retargeting is unavailable through this transport. Use the explicit Blender mapping path. There is no automatic fallback between providers, accounts, models, transports, or credit units. Refining, texturing, cancelling and other unlisted operations are not implemented here.

## Prepare and authorize

All command input JSON and downloaded artifacts are relative to the selected workspace; traversal, absolute input paths and symlinks are rejected. Tool envelopes for native local image uploads contain an absolute path derived from that checked workspace input. The connector must have access to that same path. WSL paths are not automatically translated to Windows or uploaded to another host.

Create `request.json` inside your workspace:

```json
{"prompt":"an original small geometric robot","ai_model":"meshy-t2","model_type":"smart-topology","target_polycount":4000,"topology":"triangle","target_formats":["glb"]}
```

```sh
python studio/studio.py --workspace /absolute/local/workspace provider prepare --provider meshy --operation text-to-3d --body request.json
python studio/studio.py --workspace /absolute/local/workspace provider show --job JOB_ID
```

Preparation persists a request fingerprint, exact provider/tool/transport, declared context, input paths and SHA-256 hashes before submission. An identical fingerprint is refused, including after a process restart. The error identifies the existing job to resume. Changing a source file changes the fingerprint; changing a prepared file later blocks submission intent. Local native image files are automatically hash inventoried; use repeated `--input path` for other local provenance inputs.

Use an explicit current model: native Meshy supports `meshy-7.1`, `meshy-6`, `meshy-6-lite`, `meshy-t2` and `meshy-t2.5`. Smart Topology requires `model_type: smart-topology`, triangles, and no remesh/decimation. T2 allows 100–15,000 faces; T2.5 allows 100–30,000. Standard target counts require `should_remesh: true`, and allow 100–300,000. Quad outputs need FBX/OBJ (or Blend for native remesh). Deprecated `lowpoly` and moving `latest` aliases are refused. Native text generation is a bare preview; textures require a separate unsupported stage and separate authorization. Image generation has the tool's `should_texture` default unless explicitly set.

Tripo text requires `modelVersion` (`v3.1-20260211`, `v3.0-20250812`, `v2.5-20250123`); image generation requires `model` (`tripo-v31`, `tripo-p1`, `tripo-p2`). The selected route's camelCase fields are retained. Text `generateParts` requires v3 and explicit `texture: false`; image parts require `tripo-v31` and `textureQuality: none`. Text face limits are 500–2,000,000 triangles or 500–150,000 quads. Image p1/p2 face limits are 100–20,000/50,000; v31 allows up to 2,000,000. Multiview needs 2–4 named front/left/back/right image identifiers and cannot request rigging. Tripo remesh separates retopology (maximum 20,000 triangles/10,000 quads) from simplification (2,000,000/150,000).

Meshy rig context (`--context context.json`) requires `{"bodyType":"humanoid","textured":true,"faceCount":4000}` with no more than 300,000 faces. Tripo rig context `bodyType` must match its explicit `rigType` (biped by default). These are declared eligibility inputs, not automatic geometry inspections. Native animation requires `context.parentJob` to identify a locally tracked successful Meshy rig with the exact requested `rig_task_id`. Preset actions also require `context.animationCatalogReceipt`, referencing actual catalog discovery; action IDs are never invented by the adapter. Exactly one of `action_id`, unique `action_ids` (1–10), or `motion_task_id` is accepted. A motion task's eligibility/expiry remains the operator's responsibility.

Before a paid tool call, present the exact operation, provider, model, inputs, expected cost, unit and ceiling to the user and obtain scoped authorization. The CLI does not infer current prices or transform credit units. Create `authorization.json` from that approval:

```json
{"fingerprint":"FINGERPRINT_FROM_PREPARE","provider":"meshy","transport":"native-mcp","operation":"text-to-3d","expectedCredits":5,"ceilingCredits":5,"unit":"meshy credits","approvedBy":"user","approvalReference":"reference to the explicit scoped approval"}
```

The sample amount is illustrative, not a quote. Tripo uses `magnific credits` from that account's reported quote. A missing/zero budget refuses intent; `--budget` must cover the explicitly authorized ceiling.

```sh
python studio/studio.py --workspace /absolute/local/workspace provider intent --job JOB_ID --authorization authorization.json --budget 5
```

Intent is recorded before invoking the exact prepared tool once through Codex's rediscovered connector. It is a durable guard, not proof that the remote call occurred. The CLI cannot independently authenticate human approval text; the calling agent must obtain it. It cannot prevent an operator bypassing the CLI and calling a connector manually.

## Receipt intake and recovery

Save the actual structured tool response inside the workspace (for example `receipt.json`); do not commit raw receipts or local downloads. The adapter accepts MCP `structuredContent`, JSON text `content`, or the unwrapped JSON result. Native create/status receipts bind `task_id`; Magnific create responses unwrap exactly one `creation`/`creations` entry, while `creations_get` uses its identifier/status object. Errors and malformed/unknown statuses are rejected. Intake sanitizes secret-keyed fields, bearer tokens, and URL credentials/query strings before persistence. Avoid saving raw secrets in the input receipt file itself; it remains operator-owned and local.

```sh
python studio/studio.py --workspace /absolute/local/workspace provider receipt --job JOB_ID --receipt receipt.json
python studio/studio.py --workspace /absolute/local/workspace provider resume --job JOB_ID --attempt 0
```

Resume returns a read-only status tool envelope and bounded guidance (12 attempts, delay 5–60 seconds). Native status uses `wait: false`. It performs no polling or sleeping itself. A provider `TIMEOUT` outcome is a timed-out wait, not task failure. Continue with the bound identifier. Terminal states cannot regress; stale sequence receipts (when supplied) and running-to-pending updates are preserved as ignored events. Repeated matching terminal receipts can enrich reported cost or outputs. Actual provider costs are recorded in their original unit and flagged if above the authorized ceiling. No refund is assumed.

On a create timeout/network/5xx, immediately mark an unknown outcome:

```sh
python studio/studio.py --workspace /absolute/local/workspace provider unknown --job JOB_ID --reason 'create timed out; remote outcome unknown'
```

A submission intent without an ID also needs reconciliation after a crash, even if `unknown` was never recorded. Rediscover the selected connector, list/search tasks in the same account and operation, and match prompt/input/time evidence. Supply `evidence.json`:

```json
{"decision":"bind","task_id":"EXISTING_REMOTE_ID","evidence":"reference to the actual matching task-list receipt and the match criteria"}
```

```sh
python studio/studio.py --workspace /absolute/local/workspace provider reconcile --job JOB_ID --evidence evidence.json
```

A task ID cannot be rebound or claimed by a different job on the same provider/transport. A missing task in a list is not permission to submit again: no automatic reset/retry-create route exists. Do not alter request content to evade duplicate guards. If no connector is exposed in a new chat, report BLOCKED and retain the job. Reconciliation evidence is operator-supplied; preserve the real task-list receipt separately for audit.

## Download and validate

Successful native jobs return a fresh download-tool envelope with an unused destination inside the workspace. Magnific instructions fetch a fresh temporary URL via `creations_get` and save the model inside that workspace. Sanitized historical URLs omit signed query credentials and may be unusable; rediscover and fetch a new authorized URL. Neither route downloads from repository code.

```sh
python studio/studio.py --workspace /absolute/local/workspace provider intake --job JOB_ID --source download.glb --sha256 ACTUAL_SHA256
```

Intake requires success, exact SHA-256, checked local source, and core GLB validation. It copies into a unique immutable output and records source/hash/task lineage. It refuses repeated identical intake, malformed containers and non-GLB output in this initial implementation. FBX/OBJ may be generated by provider tools but require their own validated adapter before promotion. Intake is technical evidence only; it grants no visual/content/provenance gate and creates no reviewed Asset/package automatically.

Jobs are stored under `provider-jobs/JOB_ID/request.json` and immutable numbered `event-*.json` snapshots, with separate downloaded outputs. Concurrent writers use a short exclusive local lock. A crash can leave a lock: verify no process is writing before manually removing that lock; never remove a live one. Store jobs in an ignored local workspace, outside preview/package allowlists. Full receipt files remain local; distributable reports must use sanitized event data and an explicit reviewed inventory.

## Verification boundary

`python3 -m unittest discover -s studio/tests -p test_providers.py -v` tests real local persistence, lifecycle, payload validation, paths, hashes, GLB intake and redaction with schema-shaped native/Magnific fixtures. Fixtures are not recorded live service results. This implementation makes no paid call and has no live-provider PASS. Tool schemas were inspected from exposed MCP metadata on 2026-10-30; rediscover before a future submission because provider contracts may change. No live balance, quote, task submission, status, download or cancellation was performed.
