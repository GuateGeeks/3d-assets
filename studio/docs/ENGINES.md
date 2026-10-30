# Local engines and motion interchange

The backend group separates implementation, configuration, and runtime evidence.
Adapter `describe(settings)` is exposed through unified capability discovery; configured
paths do not imply a verified environment. A successful process or structural
container check does not approve deformation, appearance, content, or rights.

## Blender CPU

Configure `blender.python` as an existing Python with bpy, or
`blender.executable` as an existing Blender executable. No environment is copied,
symlinked, installed, or modified. Input paths are relative to the Studio workspace.

```
python studio/studio.py backend blender demo
python studio/studio.py backend blender inspect --input incoming/model.glb
python studio/studio.py backend blender export --input incoming/model.blend
python studio/studio.py backend blender retarget --input incoming/target.blend --motion incoming/motion.blend --mapping incoming/mapping.json
```

`demo` creates a 0.3 m rigid cube with a one-second turn, distinct from organic
inference. `export` and `retarget` save a new scene.blend and asset.glb, reopen the
blend, then import the GLB into an empty scene. Checks compare mesh/armature counts,
physical bounds and clip durations in seconds at the same FPS. Bone-display helper
meshes are excluded from asset geometry counts. Exports scope the active scene and
active actions. No visual review is implied. FBX, OBJ, GLB/glTF and blend can be
inspected/exported. Self-contained GLB is the preferred interchange artifact.

The bpy 4.2 wheel on this host exits nonzero during teardown after successful glTF
I/O. The worker follows the existing laboratory convention: synchronously complete
validation and JSON/log writes, catch failures, flush, then os._exit(actualStatus)
for standalone Python. An exception still yields nonzero status; Blender executable
mode uses its normal lifecycle. Optional Draco is unavailable in the observed runtime;
these probes use uncompressed GLB.

Blender is Z-up, glTF is Y-up. The glTF importer/exporter owns that conversion.
`retarget.convert_vector` explicitly converts Z-up (x,y,z) to Y-up (x,z,-y), and
inversely (x,y,z) to (x,-z,y). It preserves physical scale. No implicit 2 m
normalization occurs in Blender operations. `dimensionsMeters` includes the Blender
scene unit scale. Clips currently describe active/NLA-associated actions, not every
orphan action in a blend datablock.

## One explicit humanoid mapping

`retarget.MIXAMO_TO_HUMANOID` is a 20-bone source-name to target-name map: Hips,
Spine/Spine1/Spine2, Neck/Head, left/right Shoulder/Arm/ForeArm/Hand and
UpLeg/Leg/Foot. Source names have the `mixamorig:` prefix; target names are hips,
spine/chest/upper_chest, neck/head, clavicle/upper_arm/forearm/hand and thigh/shin/foot
with `.L`/`.R` suffixes. A JSON object can provide another explicit map.

This supported profile requires matching rest axes (0.001 rad tolerance), mapped
parent hierarchy, applied object rotation/scale, one source action and one source
and target armature. Different rest axes are rejected. Each integer source frame
bakes local quaternion rotations; target bone lengths stay fixed, and root
translation is copied in scene units. Source and target must already use meters
and the same scene FPS. Arbitrary BVH conventions, rest-pose correction, IK,
foot-contact cleanup, fingers and automatic skeleton matching are outside this
profile. The CPU fixture verifies an actual pi/4 midpoint arm rotation, not only
clip names. Production movement and deformation need visual review.

## Existing UniRig runner

Configure `unirig.laboratoryRoot` as the existing 3d-assets checkout and
`unirig.python` as its existing runtime. `--input` is a candidate JSON manifest,
not a bare mesh. These are the real existing CLI commands:

```
python studio/studio.py backend unirig ingest --input incoming/candidate.json --dry-run
python studio/studio.py backend unirig rig --input incoming/creation-prepared.json --dry-run
```

Execution delegates to `<laboratoryRoot>/lab/lab.py ingest --candidate ... --timeout
...` or `rig --candidate ... --stage all --timeout ...`. The existing runner owns
its exclusive `lab/.local/locks/unirig.lock`, explicit 2 m preparation, restoration
of original physical scale/materials, per-stage logs and immutable child run.
The adapter records the exact command, snapshots the successful child JSON receipt
and its SHA-256 into its own new Studio run, and returns the restored candidate
reference. It does not bypass the known pipeline with generic upstream shell
scripts. Candidate contracts and source confinement remain enforced by the existing
runner. The laboratory checkout must explicitly be writable for future runs and
mutable report pointers. Existing reviewed runs remain intact. Dry-run reports the
write/lock locations without running the child. No UniRig GPU inference was run in
this implementation task.

The pinned existing UniRig upstream revision is
`6793c6640ff01c8fb389f3993434124bb43d2933`. Official scripts use separate skeleton and
skin stages and unsafe shell eval on arguments; Studio does not invoke those scripts
directly. Primary reference:
https://github.com/VAST-AI-Research/UniRig/tree/6793c6640ff01c8fb389f3993434124bb43d2933

## SkinTokens local or configured SSH

`contracts/skintokens-profile.json` pins the official repository revision
`273b691d35989d71cd17ff2895fdc735097b92d1`, verified with git ls-remote on
2026-10-30. Official `demo.py` CLI supports --input, --output, --model_ckpt,
--use_transfer and --use_skeleton. `hfPath` is optional; if supplied it must be a
complete local model directory suitable for upstream's AutoModel.from_pretrained,
not merely a downloaded config. No model/weight download or setup runs automatically.

Configure `skintokens.repositoryRoot`, `python`, `checkpoint`, optionally `hfPath`,
`executor` (local or ssh), `timeoutSeconds` (1..7200), and for SSH `host` and
`stagingRoot`. Paths must be safe absolute POSIX paths, with no traversal or shell
metacharacters. The profile's revision cannot be relaxed. Local inference also
requires root setting `sharedGpuLock` pointing to the existing laboratory lock.
It is opened read-only with flock, preserving prior metadata, while Studio also
holds its own workspace heavy-job lock. SSH holds a remote staging-root flock.
Configure all remote heavy-job users to use the same lock.

```
python studio/studio.py backend skintokens rig --input incoming/static.glb --dry-run
```

Studio accepts self-contained GLB intake. Existing skins are preserved by default;
explicit --use-skeleton requests upstream reskinning. Dry-run validates the profile
and reports the real command with NOT_RUN status; it never implies a passed GPU
preflight. Live preflight verifies exact Git HEAD, clean tracked source, configured
files, and >=14336 MiB total AND free NVIDIA memory. Inference is offline. Source
files are copied from Git-tracked regular files into the new run, preserving the
configured source and environment. Local inputs are staged and hash-bound. GPU
inference requires all upstream model dependencies already available; missing
secondary weights/configs fail normally, without downloading or reporting success.

SSH explicitly stages into a new unique directory, archives the pinned source,
copies the input and a stdlib supervisor, checks the remote input hash, holds flock,
and executes the pinned official command. The supervisor bounds execution and
terminates owned detached child sessions (including bpy's separate session) on
interruption or timeout. The returned output must match its remote SHA-256 and the
original input hash; local intake rejects traversal and symlinks and requires a
GLB containing both mesh and skin. Stage artifacts are retained as evidence, with
no automatic deletion. SSH/model execution remains NOT_RUN without an eligible
configured host; local supervisor behavior is tested with ordinary CPU children.

Primary references checked 2026-10-30:
- https://github.com/VAST-AI-Research/SkinTokens/tree/273b691d35989d71cd17ff2895fdc735097b92d1
- https://github.com/VAST-AI-Research/SkinTokens/blob/273b691d35989d71cd17ff2895fdc735097b92d1/demo.py
- https://github.com/VAST-AI-Research/SkinTokens/blob/273b691d35989d71cd17ff2895fdc735097b92d1/README.md

## Verification

```
python3 -m unittest studio.tests.test_local -v
STUDIO_BPY_PYTHON=/absolute/existing/python python3 -m unittest studio.tests.test_local -v
```

The second command runs real CPU bpy fixtures in temporary directories. It does
not run inference, install dependencies, inspect user assets, or claim visual QA.
Implementation evidence is linked by the assigned SDD task report.
