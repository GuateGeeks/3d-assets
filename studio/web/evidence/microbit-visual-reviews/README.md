# micro:bit V2 Studio visual reviews, 2026-10-31

Three independent visual and content reviews of the micro:bit V2 product captures
(production preview, software rendering). Each was done by a different fresh-context
reviewer who opened the PNGs of one capture folder, five reference photos and their
own crops, without seeing the other reviews. The result was FAIL, FAIL, then PASS:
each failure led to a Studio-side change (never a new Blender run) and a new capture
folder. Verdicts use `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`; visual and content are
judged separately.

| Verdict file (verbatim copy) | Judged evidence folder | Visual | Content | sha256 of the verdict file |
|---|---|---|---|---|
| `r1-studio-visual-review.json` | `../microbit-20261031/` | FAIL | FAIL | `fd5769b5af9ea4942337b6aed32e1b057767043631e11a7c1726ba23052f98a7` |
| `r2-studio-visual-review.json` | `../microbit-20261031-r2/` | FAIL | FAIL | `4634eec428e0e38ec3bddc0c5b165fd4565646490c9f23139074bc9c96f5c5a7` |
| `r3-studio-visual-review.json` | `../microbit-20261031-r3/` | PASS | PASS | `7b028c4fa5a8c9573ec455e2bbd6fb7238a859a91261126f96f473d706723a46` |

The three `.json` files are byte-identical copies of the reviewers' output; they are
not edited. Their `openedImages` lists keep the paths the reviewers used (some point at
session scratch files that are not preserved, for example their own crops).

## Round 1: FAIL / FAIL

Folder `../microbit-20261031/`. The captured channels were right (16, 7 and 5 lit LEDs
at the receipt positions, verified on 2x crops) but the look was not: lit LEDs were
a pale pink (about RGB 255,237,229) next to unlit LEDs that were bright off-white
(about 237,233,228), so at normal size a student could not tell lit from unlit and the
heart, smiley and check mark were not recognisable. The oblique default camera also
skewed the grid. Blocking: lit LED colour, unlit LED colour. Fix (Studio side, GLB
unchanged): the factory applies a dark LED rest look and a saturated red emissive look
with an intensity that follows the brightness value.

## Round 2: FAIL / FAIL

Folder `../microbit-20261031-r2/`. The LED look was now good (orange-red lit against
dark brown unlit, lit counts exactly 16 / 7 / 5, the dim mouth LEDs of the smile
distinguishable from the eyes). It failed on the viewer's default camera: about 24
degrees above the board and about 35 degrees off-axis, with the LED matrix only about
300 x 130 px of the 1152 x 820 canvas, so the grid was squashed and the patterns were
readable only in the extra top-down views, which are not the product default.
Blocking: default camera elevation, orientation and framing. Fix (Studio side): an
optional authored scene `camera` and a preview framing that fits the board.

## Round 3: PASS / PASS

Folder `../microbit-20261031-r3/`. At the scene's authored default camera (elevation
62, azimuth 0) the board fills about 73 % of the canvas width, the USB end is at the
top and the LED rows are horizontal. Lit LEDs (about RGB 255,104,67) stand out against
the dark unlit LEDs (about 44,31,27); the heart (16), smiley (7) and check mark (5)
are recognisable without zooming and match the receipt channels LED for LED. The
reviewer listed non-blocking defects (see `studio/docs/STATUS.md`): no A/B/pin
markings on the board, a slate-grey PCB, 0.5 mm button travel invisible at the default
camera, mouth corners as bright as the eyes, the close-up Board label over a lit LED,
no contact shadow, board low in frame.

## Reviewer identity (caveat)

All three reviewers are recorded as actor `unknown-subagent-fresh-context`, model
`claude-opus-5-5`, effort `medium`. These are the requested values; the runtime did
not confirm the model or effort actually served, and no agent identifier was
available. A fresh context means the reviewer had no access to the author's reasoning
or to earlier reviews; it is not an attestation of the backend. The reviews rest on
what the reviewers saw in the images and on the hashes they recomputed.

## Preservation

The evidence folders `../microbit-20261031/`, `../microbit-20261031-r2/` and
`../microbit-20261031-r3/` are preserved unmodified as the evidence that was
reviewed. Rounds 1 and 2 are kept even though they FAILED and are not an approval of
the shipped product look. A capture is evidence; these verdicts are not a GPU
performance result and say nothing about live MakeCode simulator wiring (`NOT_RUN`).
